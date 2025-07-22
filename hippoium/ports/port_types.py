from __future__ import annotations
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
    "TokenCount","ContextQuery","ContextBundle"
,"ChatTurn"]

from dataclasses import dataclass, field
import enum
from enum import Enum, auto
from typing import Literal, List, Dict, Any, Optional





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


class Role(str, enum.Enum):
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