from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from hippoium.core.utils.time import utc_now


@dataclass
class Message:
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MemoryItem:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ToolSpec:
    name: str
    description: str | None = None
    args_schema: dict[str, Any] | None = None

    @property
    def parameters(self) -> dict[str, Any]:
        return self.args_schema or {}

    @parameters.setter
    def parameters(self, value: dict[str, Any]) -> None:
        self.args_schema = value


@dataclass
class RetrievalResult:
    text: str
    score: float
    source: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    token_budget: int = 4096
    cache_tiers: dict[str, Any] = field(default_factory=dict)
    provider: dict[str, Any] = field(default_factory=dict)
    request_timeout_s: int | None = None
    default_model: str | None = None
    max_messages: int | None = None
    cache_ttl_s: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)
