"""
Abstract Adapter – framework agnostic bridge.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List


class BaseAdapter(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    def embeddings(self, text: str) -> list[float]: ...

    def embed(self, texts: Iterable[str], **kwargs: Any) -> List[List[float]]:
        return [self.embeddings(text, **kwargs) for text in texts]

    # Shared helper
    def _parse_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return kwargs
