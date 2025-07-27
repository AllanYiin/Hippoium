from contextlib import AbstractContextManager
from contextvars import ContextVar
from typing import Optional, List, Any

# We'll reuse MemoryItem, ToolSpec from ports, and hook_registry from core.hooks
try:
    from hippoium.ports.mcp import MemoryItem, ToolSpec
except ImportError:
    # Fallback definitions if needed
    class MemoryItem:
        def __init__(self, content: str, metadata: Optional[dict] = None):
            self.content = content
            self.metadata = metadata

    class ToolSpec:
        def __init__(self, name: str, description: Optional[str] = None):
            self.name = name
            self.description = description

from hippoium.core.hooks import hook_registry

# Context variable to track the current context session (for context_api usage)
current_context_session: ContextVar[Optional["PromptContextSession"]] = ContextVar("current_context_session", default=None)

class PromptContextSession(AbstractContextManager):
    """
    Context manager for context injection. Collects memory, negative examples, etc.,
    and builds a combined prompt with context when used in a `with` block.
    """
    def __init__(self, memory: Optional[Any] = None, cache_ttl: Optional[int] = None, rag: bool = False) -> None:
        """
        Initialize a context session.
        :param memory: Optional memory backend or config (e.g., "redis" or a config dict).
        :param cache_ttl: Optional cache TTL for context (not implemented in this pure version).
        :param rag: Whether to enable retrieval-augmented generation (RAG) features.
        """
        # Configuration (not fully utilized in this core context manager)
        self.memory_config = memory
        self.cache_ttl = cache_ttl
        self.rag_enabled = rag
        # Collected context data
        self.memory_items: List[MemoryItem] = []
        self.negative_examples: List[str] = []
        self.tools: List[ToolSpec] = []
        self.history_prompts: List[str] = []
        self.rag_results: List[Any] = []
        # (If a memory backend was provided, initialize it here if needed)

    def __enter__(self) -> "PromptContextSession":
        # Set this session as current in the context variable
        self._token = current_context_session.set(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Optional[bool]:
        # Restore previous context session (end of with-block)
        current_context_session.reset(self._token)
        # Do not suppress exceptions (return False)
        return False

    def add_memory(self, content: str, metadata: Optional[dict] = None) -> None:
        """Add a piece of contextual memory (e.g., prior conversation or relevant fact)."""
        item = MemoryItem(content=content, metadata=metadata)
        self.memory_items.append(item)

    def add_negative_example(self, content: str) -> None:
        """Add a negative example or instruction to avoid certain types of content."""
        self.negative_examples.append(content)

    def add_tool(self, name: str, description: str = "") -> None:
        """Register an available tool in this context (for potential tool usage via MCP)."""
        tool = ToolSpec(name=name, description=description)
        self.tools.append(tool)

    def build(self, prompt: str) -> str:
        """
        Build an enhanced prompt by injecting collected context (memory, negative examples, etc.)
        into the original prompt. Returns the combined prompt string.
        """
        # If RAG is enabled, trigger hook before performing retrieval (e.g., to fetch external context)
        if self.rag_enabled:
            hook_registry.notify("before_rag_query", query=prompt, context=self)
            # (A hook could populate self.rag_results or self.memory_items with retrieved data)
        # If there is a lot of memory content, trigger compression hooks
        if len(self.memory_items) > 50:
            hook_registry.notify("before_compression", context=self)
            # Simple compression: keep only the last 50 memory items (placeholder for actual compression logic)
            self.memory_items = self.memory_items[-50:]
            hook_registry.notify("after_compression", context=self)
        # Trigger hooks before injecting prompt (e.g., for negative examples)
        hook_registry.notify("before_prompt_injection", context=self)
        # Construct the final prompt string
        parts: List[str] = []
        if self.negative_examples:
            # Include negative examples as preamble lines/instructions
            parts.extend(self.negative_examples)
        if self.memory_items:
            # Include memory content (each memory item's content in context)
            parts.extend([m.content for m in self.memory_items])
        # Finally, append the original prompt
        parts.append(prompt)
        enhanced_prompt = "\n".join(parts)
        # Record this prompt in history
        self.history_prompts.append(prompt)
        return enhanced_prompt

# Convenience function to create a PromptContextSession via context manager
def context_session(*args, **kwargs) -> PromptContextSession:
    """
    Create a new PromptContextSession. Usage:
        with context_session(memory=config, rag=True) as ctx:
            ...  # use ctx to add memory, negative examples, then ctx.build(prompt)
    """
    return PromptContextSession(*args, **kwargs)