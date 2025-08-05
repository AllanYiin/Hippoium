"""
universal_chunker.py
────────────────────
A dependency-light, strategy-pluggable chunker for Hippoium.

• 支援 fixed / recursive / sentence / semantic 四種內建策略
• 自動處理中西語句號差異，避免縮寫、小數誤切
• 產生唯一 ID 與前後關係圖，並預留 embedding 欄位
• 可用 register_strategy 新增自訂 Chunker
"""

from __future__ import annotations

import itertools
import re
import uuid
from dataclasses import dataclass, field
from functools import reduce
from typing import Any, Dict, Iterable, List, Optional, Type

# ────────────────────────────────────────────────────────────────
# 1. 資料結構
# ────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    uid: str
    parent_id: str                      # 文件 / 對話 ID
    prev_id: Optional[str]
    next_id: Optional[str]
    content: str
    chunk_type: str = "text"            # text / dialog / code / image / table / formula
    lang: str = "auto"                  # "zh" / "en" / ...
    meta: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class DocGraph:
    """以 dict 儲存全部節點，便於查表存取。"""
    parent_id: str
    nodes: Dict[str, Chunk]


# ────────────────────────────────────────────────────────────────
# 2. Config
# ────────────────────────────────────────────────────────────────

@dataclass
class ChunkConfig:
    strategy: str = "recursive"         # fixed | recursive | sentence | semantic
    chunk_size: int = 400
    overlap: int = 50
    lang_hint: str = "auto"             # 可強制 "zh" / "en"
    semantic_threshold: float = 0.95    # SemanticChunker 關閉時可忽略
    custom_separators: Optional[List[str]] = None
    custom_abbr: Optional[List[str]] = None  # 供使用者擴充縮寫表


# ────────────────────────────────────────────────────────────────
# 3. BaseChunker & 工具函式
# ────────────────────────────────────────────────────────────────

DEFAULT_ABBR_EN = {
    "mr.", "mrs.", "dr.", "prof.", "sr.", "jr.", "e.g.", "i.e.",
    "etc.", "vs.", "inc.", "fig.", "approx."
}
NUMBER_DOT = re.compile(r"\b\d+\.\d+\b")  # e.g. 3.1415

class BaseChunker:
    def __init__(self, cfg: ChunkConfig):
        self.cfg = cfg
        self.abbr_set = set(DEFAULT_ABBR_EN)
        if cfg.custom_abbr:
            self.abbr_set.update(a.lower() for a in cfg.custom_abbr)

    # -------- 句子分割（考慮縮寫與小數點） --------
    def _sentences(self, text: str) -> List[str]:
        protected: Dict[str, str] = {}

        def _protect(match: re.Match[str]) -> str:
            key = f"__DOT{len(protected)}__"
            protected[key] = match.group(0)
            return key

        # 保護小數
        text = NUMBER_DOT.sub(_protect, text)

        # 保護縮寫
        for abbr in self.abbr_set:
            if abbr in text.lower():
                escaped = re.escape(abbr)
                text = re.sub(escaped, _protect, text, flags=re.IGNORECASE)

        # 中西方句點分割
        parts = re.split(r"(?<=[。！？.!?])\s+", text)

        # 還原
        def _restore(s: str) -> str:
            for k, v in protected.items():
                s = s.replace(k, v)
            return s

        return [ _restore(p) for p in parts if p.strip() ]

    # 子類需實作
    def split(self, text: str) -> Iterable[str]:  # pragma: no cover
        raise NotImplementedError


# ────────────────────────────────────────────────────────────────
# 4. 策略實作
# ────────────────────────────────────────────────────────────────

class FixedChunker(BaseChunker):
    def split(self, text: str) -> Iterable[str]:
        chars = list(text)                           # 以字符近似 token，避免外部 tokenizer
        size, ov = self.cfg.chunk_size, self.cfg.overlap
        for i in range(0, len(chars), size - ov):
            yield "".join(chars[i:i + size])


class RecursiveChunker(BaseChunker):
    def split(self, text: str) -> Iterable[str]:
        seps = self.cfg.custom_separators or ["\n\n", "\n", "。", ".", " ", ""]
        chunks = [text]
        for sep in seps:
            new_chunks: List[str] = []
            for chunk in chunks:
                if len(chunk) <= self.cfg.chunk_size:
                    new_chunks.append(chunk)
                    continue
                # 依 sep 再切
                parts = chunk.split(sep)
                buf = ""
                for part in parts:
                    if len(buf) + len(part) <= self.cfg.chunk_size:
                        buf += part + sep
                    else:
                        new_chunks.append(buf)
                        buf = part + sep
                if buf:
                    new_chunks.append(buf)
            chunks = new_chunks

        # 處理 overlap
        ov = self.cfg.overlap
        for idx, c in enumerate(chunks):
            if ov and idx:
                c = chunks[idx - 1][-ov:] + c
            yield c


class SentenceChunker(BaseChunker):
    def split(self, text: str) -> Iterable[str]:
        sentences = self._sentences(text)
        buf = ""
        size, ov = self.cfg.chunk_size, self.cfg.overlap
        for sent in sentences:
            if len(buf) + len(sent) <= size:
                buf += sent
            else:
                yield buf
                buf = sent
        if buf:
            yield buf

        # optional overlap (句子級 chunk 不太需要重疊；如需可自行開啟)
        # 實作與 Recursive 相同，這裡省略


# -------- 4.1 SemanticChunker（可選） --------
class SemanticChunker(BaseChunker):
    """
    依照相鄰句 embedding 相似度 (cosine) 進行聚合。
    • 若無 sentence-transformers，將拋出 NotImplementedError
    """
    def __init__(self, cfg: ChunkConfig):
        super().__init__(cfg)
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
        except ImportError as e:
            raise NotImplementedError(
                "SemanticChunker 需要安裝 sentence-transformers & numpy：\n"
                "    pip install sentence-transformers numpy"
            ) from e
        self.st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.np = __import__("numpy")

    def _embed(self, sents: List[str]):
        return self.st_model.encode(sents, show_progress_bar=False, normalize_embeddings=True)

    def split(self, text: str) -> Iterable[str]:
        sents = self._sentences(text)
        if not sents:
            return
        embs = self._embed(sents)
        np = self.np

        buf, buf_len = "", 0
        size, ov, thresh = self.cfg.chunk_size, self.cfg.overlap, self.cfg.semantic_threshold

        for i, sent in enumerate(sents):
            if buf_len + len(sent) <= size:
                buf += sent
                buf_len += len(sent)
                continue

            # 若已達 chunk_size，上下句再判 cosine
            if i + 1 < len(embs):
                cos = float(np.dot(embs[i], embs[i + 1]))
            else:
                cos = 0.0
            if cos < thresh or buf_len >= size:
                yield buf
                # overlap by chars
                buf = sent if ov == 0 else (buf[-ov:] + sent)
                buf_len = len(buf)
            else:
                buf += sent
                buf_len += len(sent)

        if buf:
            yield buf


# ────────────────────────────────────────────────────────────────
# 5. Strategy Registry
# ────────────────────────────────────────────────────────────────

_STRATEGIES: Dict[str, Type[BaseChunker]] = {
    "fixed": FixedChunker,
    "recursive": RecursiveChunker,
    "sentence": SentenceChunker,
    "semantic": SemanticChunker,
}

def register_strategy(name: str, cls: Type[BaseChunker]) -> None:
    """供外部擴充，例如 PPLChunker / S2Chunker / LLMChunker 等。"""
    _STRATEGIES[name] = cls


def get_strategy(name: str) -> Type[BaseChunker]:
    if name not in _STRATEGIES:
        raise ValueError(f"Unknown chunking strategy: {name}")
    return _STRATEGIES[name]


# ────────────────────────────────────────────────────────────────
# 6. Graph Builder
# ────────────────────────────────────────────────────────────────

def build_graph(chunks_iter: Iterable[str],
                parent_id: str,
                chunk_type: str = "text") -> DocGraph:
    graph = DocGraph(parent_id=parent_id, nodes={})
    prev_uid: Optional[str] = None
    for content in chunks_iter:
        uid = str(uuid.uuid4())
        node = Chunk(uid=uid,
                     parent_id=parent_id,
                     prev_id=prev_uid,
                     next_id=None,
                     content=content,
                     chunk_type=chunk_type)
        if prev_uid:
            graph.nodes[prev_uid].next_id = uid
        graph.nodes[uid] = node
        prev_uid = uid
    return graph


# ────────────────────────────────────────────────────────────────
# 7. 簡易 Block 抽取（圖片 / 表格 / 代碼 / 公式）
# ────────────────────────────────────────────────────────────────

_BLOCK_PATTERNS = {
    "code": re.compile(r"```.*?```", re.S),
    "image": re.compile(r"!\[.*?\]\(.*?\)"),
    "table": re.compile(r"(\|.+?\|(?:\s*\n\|.+?\|)+)"),        # markdown table
    "formula": re.compile(r"\$\$.*?\$\$", re.S),
}

def extract_blocks(text: str) -> Dict[str, List[str]]:
    """回傳 {block_type: [block_str, ...]}，並在原文中用 placeholder 取代"""
    placeholders, counter = {}, 0
    for btype, pat in _BLOCK_PATTERNS.items():
        for match in pat.finditer(text):
            key = f"__{btype.upper()}_{counter}__"
            placeholders[key] = (btype, match.group(0))
            text = text.replace(match.group(0), f" {key} ")
            counter += 1
    return placeholders, text


#
# # ────────────────────────────────────────────────────────────────
# # 8. 全流程示範
# # ────────────────────────────────────────────────────────────────
#
# if __name__ == "__main__":
#     from pathlib import Path
#
#     raw_text = Path("sample_doc.md").read_text(encoding="utf-8")
#
#     # 抽取 block & 替換
#     blocks, cleaned_text = extract_blocks(raw_text)
#
#     # 建立 Chunker
#     cfg = ChunkConfig(strategy="recursive",
#                       chunk_size=350,
#                       overlap=50)
#     chunker_cls = get_strategy(cfg.strategy)
#     chunker = chunker_cls(cfg)
#
#     # 切分
#     parent_id = str(uuid.uuid4())
#     text_graph = build_graph(chunker.split(cleaned_text), parent_id)
#
#     # 將 block 以獨立 chunk 方式補回關係圖
#     for placeholder, (btype, content) in blocks.items():
#         uid = str(uuid.uuid4())
#         text_graph.nodes[uid] = Chunk(uid=uid,
#                                       parent_id=parent_id,
#                                       prev_id=None,
#                                       next_id=None,
#                                       content=content,
#                                       chunk_type=btype)
#         # 可在此附加 more meta 如 bbox / language 等
#
#     print(f"✅ 產生 {len(text_graph.nodes)} 個 chunk")