from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Protocol, runtime_checkable
from .schemas import Message, Artifact
# hippoium/ports/protocols.py

from abc import ABC, abstractmethod
from typing import List
from hippoium.ports.port_types import *


class ContextEngineProtocol(ABC):
    """
    最小對外介面；任何框架或 Model Context Protocol 只需依賴此抽象。
    """

    # ------------------- write ------------------- #
    @abstractmethod
    def write_turn(self, record: ContextRecord) -> None:
        ...

    # ------------------- read -------------------- #
    @abstractmethod
    def get_context_for_scope(self, query: ContextQuery) -> ContextBundle:
        ...

    # （選擇性）除錯用途：匯出目前記憶全部內容
    @abstractmethod
    def dump_memory(self) -> List[dict]:
        ...

@runtime_checkable
class Storage(Protocol):
    """Generic key-value storage interface."""

    @abstractmethod
    def get(self, key: str) -> bytes | None: ...

    @abstractmethod
    def put(self, key: str, value: bytes) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


@runtime_checkable
class CacheProtocol(Protocol):
    """Unified cache interface for memory tiers."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """Return cached value or ``None`` if absent/expired."""

    @abstractmethod
    def put(self, key: str, value: Any) -> None:
        """Store value into cache, applying eviction if necessary."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove value associated with key if present."""


class WriteBackAPI(ABC):
    """Direct write-back of large artifacts to shared store."""

    @abstractmethod
    def write(self, artifact: Artifact) -> str:
        """Persist artifact and return reference hash."""


class TokenMeter(ABC):
    @abstractmethod
    def update(self, consumed: TokenCount) -> None: ...

    @abstractmethod
    def remaining(self) -> TokenCount: ...


class RetrieverPort(ABC):
    @abstractmethod
    def search(self, request: str, top_k: int) -> List[Message]: ...


class ScorerPort(ABC):
    @abstractmethod
    def score(self, query: str, docs: Sequence[Message]) -> List[Score]: ...
