# hippoium/ports/events.py
"""
官方事件名稱列舉。使用方式：
    from hippoium.ports.events import Event
    hook_registry.register(Event.BEFORE_MEMORY_STORE, callback)

仍然允許自訂事件字串：
    hook_registry.notify("before_translation", text=...)
"""

from enum import Enum, unique


@unique
class Event(str, Enum):
    # ─────────── I/O Capture ───────────
    BEFORE_REQUEST_CAPTURE = "before_request_capture"
    AFTER_REQUEST_CAPTURE = "after_request_capture"
    BEFORE_RESPONSE_CAPTURE = "before_response_capture"
    AFTER_RESPONSE_CAPTURE = "after_response_capture"

    # ─────────── Compression ───────────
    BEFORE_COMPRESSION = "before_compression"
    AFTER_COMPRESSION = "after_compression"

    # ─────────── Memory Tiering ────────
    BEFORE_MEMORY_STORE = "before_memory_store"
    AFTER_MEMORY_STORE = "after_memory_store"
    BEFORE_MEMORY_EVICTION = "before_memory_eviction"
    AFTER_MEMORY_EVICTION = "after_memory_eviction"

    # ─────────── Auto-Label / Neg-Vault ─
    BEFORE_AUTO_LABEL = "before_auto_label"
    AFTER_AUTO_LABEL = "after_auto_label"
    BEFORE_NEGATIVE_FILTER = "before_negative_filter"
    AFTER_NEGATIVE_FILTER = "after_negative_filter"

    # ─────────── Patch / Diff ──────────
    BEFORE_PATCH_GENERATE = "before_patch_generate"
    AFTER_PATCH_GENERATE = "after_patch_generate"
    BEFORE_PATCH_APPLY = "before_patch_apply"
    AFTER_PATCH_APPLY = "after_patch_apply"

    # ─────────── RAG ───────────────────
    BEFORE_RAG_QUERY = "before_rag_query"
    AFTER_RAG_QUERY = "after_rag_query"
    BEFORE_RAG_MERGE = "before_rag_merge"
    AFTER_RAG_MERGE = "after_rag_merge"

    # ─────────── Prompt Build ──────────
    BEFORE_TEMPLATE_LOAD = "before_template_load"
    AFTER_TEMPLATE_LOAD = "after_template_load"
    BEFORE_PROMPT_INJECTION = "before_prompt_injection"
    AFTER_PROMPT_INJECTION = "after_prompt_injection"

    # ─────────── Routing / Cost ────────
    BEFORE_ROUTE_SELECT = "before_route_select"
    AFTER_ROUTE_SELECT = "after_route_select"

    # ─────────── Tools ─────────────────
    BEFORE_TOOL_SELECTION = "before_tool_selection"
    AFTER_TOOL_SELECTION = "after_tool_selection"
    BEFORE_TOOL_EXEC = "before_tool_exec"
    AFTER_TOOL_EXEC = "after_tool_exec"

    # ─────────── LLM Call ──────────────
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"

    # ─────────── Telemetry ─────────────
    BEFORE_METRICS_FLUSH = "before_metrics_flush"
    AFTER_METRICS_FLUSH = "after_metrics_flush"