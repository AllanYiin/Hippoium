"""
Package marker. Ensures 'core', 'ports', and 'adapters' are importable
when this repo is installed in editable mode.
"""

from .domain import Config, MemoryItem, Message, RetrievalResult, ToolSpec
from .protocols import Cache, EmbeddingClient, LLMClient, Retriever

__all__ = [
    "Cache",
    "Config",
    "EmbeddingClient",
    "LLMClient",
    "MemoryItem",
    "Message",
    "RetrievalResult",
    "Retriever",
    "ToolSpec",
]
