from __future__ import annotations
"""
hippoium/ports/port_types.py
───────────────────────
Pure dataclass & enum definitions for context graph.
保持零第三方依賴，僅用標準庫 typing / dataclasses / enum。
"""
__all__ = [
    "MsgLabel",
    "MemTier",
    "TrimPolicy",
    "DedupStrategy",
    "ScoreFn",
    "ArtifactType",
    "GuardAction",
    "AlertLevel",
    "PatchFormat",
    "SampleStage",
    "Score",
    "TokenCount","ContextQuery","ContextBundle","DocGraph","Chunk","GraphEdge"
,"ChatTurn","EdgeType","Artifact","Message","RetrievalRequest"]

from dataclasses import dataclass, field
from enum import Enum
import enum
from enum import Enum, auto
from typing import Literal, List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime




class MsgLabel(Enum):
    OK = auto()
    WARN = auto()
    ERR = auto()
    TODO = auto()


class MemTier(Enum):
    S = "S-Cache"
    M = "M-Buffer"
    L = "L-Vector"
    COLD = "ColdStore"


class TrimPolicy(Enum):
    KEEP_HEAD = auto()
    KEEP_TAIL = auto()
    DIFF_PATCH = auto()


class DedupStrategy(Enum):
    HASH = auto()
    MINHASH = auto()


class ScoreFn(Enum):
    POS_COS = auto()
    NEG_COS = auto()
    HYBRID = auto()


class ArtifactType(Enum):
    DF = auto()
    JSON = auto()
    CODE = auto()


class GuardAction(Enum):
    ALLOW = auto()
    SOFT_BLOCK = auto()
    HARD_BLOCK = auto()


class AlertLevel(Enum):
    INFO = auto()
    MINOR = auto()
    MAJOR = auto()
    CRITICAL = auto()


class PatchFormat(Enum):
    DELTA = auto()
    BINARY = auto()


class SampleStage(str, Enum):
    RAW = "raw"
    CLEAN = "clean"
    PAIR = "pair"


Score = float  # alias for readability
TokenCount = int


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class ChatTurn:
    role: Role
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContextRecord:
    """MCP write-side payload (= one ChatCompletion message)."""
    role: Role
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ContextQuery:
    """MCP read-side payload (scope & filter)."""
    scope: str          # "user" | "task" | "topic"
    key: str            # user-id / task-id / topic-label
    prompt: str         # current user prompt (for relevance)
    template_id: str = "default"
    exclude_err: bool = True
    include_negative_ids: Optional[List[str]] = None

@dataclass
class ContextBundle:
    """Returned to MCP — already是 prompt messages list."""
    messages: List[Dict[str, str]]    # role/content dict list



class EdgeType(str, Enum):
    NEXT       = "next"        # 線性順序：A → B
    PREV       = "prev"        # 線性順序：B → A
    BELONGS_TO = "belongs_to"  # Chunk → Document/Dialogue
    EMBEDS     = "embeds"      # Doc   → Image/Table/Code
    REF        = "ref"         # 一般引用（超連結、footnote 等）
    CUSTOM     = "custom"      # 外掛自訂


@dataclass
class Chunk:
    uid: str
    parent_id: str
    content: str
    chunk_type: str = "text"           # text / dialog / code / image / table / formula
    lang: str = "auto"
    meta: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class GraphEdge:
    src: str
    dst: str
    rel: EdgeType
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocGraph:
    parent_id: str
    nodes: Dict[str, Chunk]
    edges: List[GraphEdge] = field(default_factory=list)  # ★ 加這行


    # —— utility helpers ——
    def iter_out(self, uid: str, rel: EdgeType | None = None):
        for e in self.edges:
            if e.src == uid and (rel is None or e.rel == rel):
                yield e


class Message(BaseModel):
    id: str
    role: str  # user / assistant / system
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    label: MsgLabel | None = None


class Artifact(BaseModel):
    id: str
    type: ArtifactType
    data: Any
    checksum: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
