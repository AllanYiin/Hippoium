from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from hippoium.core.utils.time import utc_now

@dataclass
class Message:
    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MemoryItem:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolSpec:
    name: str
    description: Optional[str] = None
    args_schema: Optional[Dict[str, Any]] = None

    @property
    def parameters(self) -> Dict[str, Any]:
        return self.args_schema or {}

    @parameters.setter
    def parameters(self, value: Dict[str, Any]) -> None:
        self.args_schema = value


@dataclass
class RetrievalResult:
    text: str
    score: float
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    token_budget: int = 4096
    cache_tiers: Dict[str, Any] = field(default_factory=dict)
    provider: Dict[str, Any] = field(default_factory=dict)
    request_timeout_s: Optional[int] = None
    default_model: Optional[str] = None
    max_messages: Optional[int] = None
    cache_ttl_s: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)
