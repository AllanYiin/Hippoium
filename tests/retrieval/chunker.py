"""
hippoium/tests/test_universal_chunker.py
────────────────────────────────────────
Unit tests for universal_chunker.py (including source-annotation checks).
Run:
    python -m unittest hippoium.tests.test_universal_chunker
"""
import unittest
from importlib import import_module

uc     = import_module("hippoium.core.retriever.universal_chunker")
types  = import_module("hippoium.ports.port_types")

ChunkConfig = uc.ChunkConfig
EdgeType    = types.EdgeType

# ──────────────────────────────
SIMPLE_MD = (
    "Mr. Wang bought 1.414 pies.\n\n"
    "![pic](img.png)\n"
    "```python\nprint('hi')\n```\n"
    "Another sentence."
)

# — util —
def make_chunker(strategy, **kw):
    cfg = ChunkConfig(strategy=strategy, **kw)
    return uc.get_strategy(strategy)(cfg)

# ──────────────────────────────
class SourceAnnotationTest(unittest.TestCase):
    """驗證 Graph 內是否正確出現 BELONGS_TO 與 EMBEDS 標註"""

    def test_blocks_and_edges(self):
        # 1️⃣ 抽取 blocks 及 placeholder
        blocks, cleaned = uc.extract_blocks(SIMPLE_MD)

        # 2️⃣ 分塊
        chunker = make_chunker("recursive", chunk_size=60, overlap=0)
        parent  = "doc-src-001"
        graph   = uc.build_graph(chunker.split(cleaned), parent_id=parent)

        # 3️⃣ 將 blocks 補回 (如官方範例)
        for _, (btype, content) in blocks.items():
            bid = f"block-{btype}"
            graph.nodes[bid] = types.Chunk(
                uid=bid, parent_id=parent, content=content, chunk_type=btype
            )
            graph.edges.append(types.GraphEdge(src=parent, dst=bid,
                                               rel=EdgeType.EMBEDS))

        # — 斷言 —
        # (a) 每個 chunk 皆至少有一條 BELONGS_TO
        for uid, node in graph.nodes.items():
            if node.chunk_type != "text" and node.chunk_type != "dialog":
                continue
            self.assertTrue(
                any(e for e in graph.edges
                    if e.src == uid and e.dst == parent and
                       e.rel == EdgeType.BELONGS_TO),
                f"{uid} missing BELONGS_TO"
            )

        # (b) parent → block 的 EMBEDS
        embed_edges = [e for e in graph.edges if e.rel == EdgeType.EMBEDS]
        self.assertEqual(len(embed_edges), len(blocks))
        for e in embed_edges:
            self.assertEqual(e.src, parent)
            self.assertIn(e.dst, graph.nodes)
            self.assertIn(graph.nodes[e.dst].chunk_type, {"image", "code"})

        # (c) 確保 text chunk 內不含原始 block（placeholder 已被替換）
        text_concat = " ".join(
            n.content for n in graph.nodes.values() if n.chunk_type == "text"
        )
        for _, (_, raw) in blocks.items():
            self.assertNotIn(raw.strip(), text_concat)
