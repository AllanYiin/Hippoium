"""
hippoium/ports/types.py
───────────────────────
Pure dataclass & enum definitions for context graph.
保持零第三方依賴，僅用標準庫 typing / dataclasses / enum。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .port_types import MsgLabel, ArtifactType

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
    edges: List[GraphEdge] = field(default_factory=list)

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
