
from typing import Any, List
from hippoium.core.context_manager import current_context_session

def get_recent_memory(count: int = 5) -> List[Any]:
    """
    Return the most recent memory items from the current context (up to `count` items).
    Each item may be a MemoryItem or similar object containing memory content.
    """
    ctx = current_context_session.get()
    if ctx is None:
        return []
    return ctx.memory_items[-count:]

def get_negative_examples() -> List[str]:
    """
    Return the list of negative examples (forbidden or guiding instructions) in the current context.
    """
    ctx = current_context_session.get()
    if ctx is None:
        return []
    return list(ctx.negative_examples)

def get_available_tools() -> List[Any]:
    """
    Return the list of available tools (ToolSpec objects) in the current context.
    """
    ctx = current_context_session.get()
    if ctx is None:
        return []
    return list(ctx.tools)

def get_history_prompts() -> List[str]:
    """
    Return the history of prompts that have been built in the current context session.
    """
    ctx = current_context_session.get()
    if ctx is None:
        return []
    return list(ctx.history_prompts)

def get_rag_sources() -> List[Any]:
    """
    Return the list of RAG (retrieval-augmented generation) source data from the current context.
    For example, documents retrieved via a retriever hook.
    """
    ctx = current_context_session.get()
    if ctx is None:
        return []
    # If RAG results are stored separately
    if hasattr(ctx, "rag_results"):
        return list(ctx.rag_results)
    # Otherwise, if RAG content was added to memory_items, one could filter those
    return []