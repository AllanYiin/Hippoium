from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Protocol, runtime_checkable
from .schemas import Message, Artifact
from .types import Score, TokenCount


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
