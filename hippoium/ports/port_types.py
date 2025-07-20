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
    "TokenCount",
]

from enum import Enum, auto
from typing import Literal


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