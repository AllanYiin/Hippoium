"""
Abstract Adapter – framework agnostic bridge.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any


class BaseAdapter(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    def embeddings(self, text: str) -> list[float]: ...

    def embed(self, texts: Iterable[str], **kwargs: Any) -> list[list[float]]:
        return [self.embeddings(text, **kwargs) for text in texts]

    # Shared helper
    def _parse_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        return kwargs
