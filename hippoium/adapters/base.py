"""
Abstract Adapter – framework agnostic bridge.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    name: str

    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    def embeddings(self, text: str) -> list[float]: ...

    # Shared helper
    def _parse_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        return kwargs
