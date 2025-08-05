from collections import deque
from datetime import timedelta
from typing import Optional, Dict, List, Any
from hippoium.ports.protocols import ContextEngineProtocol
from hippoium.core.memory import stores  # assuming stores.py defines SCache, MBuffer, LVector
from hippoium.ports.mcp import MemoryItem

class DefaultContextEngine(ContextEngineProtocol):
    """
    Default implementation of ContextEngineProtocol that manages S/M/L memory tiers
    and handles conversation record input processing.
    """
    def __init__(self, max_messages:int=50, max_tokens:int=2048,
                 session_ttl:Optional[timedelta]=timedelta(minutes=30)):
        # S-tier: session cache (stores entire conversation history by session ID)
        self.s_cache = stores.SCache(ttl=session_ttl)
        # M-tier: short-term buffer (recent messages with limits)
        self.m_buffer = stores.MBuffer(max_messages=max_messages, max_tokens=max_tokens)
        # L-tier: long-term vector store (archive or knowledge base)
        self.l_vector = stores.LVector(capacity=None)
        # Track current session ID for context (could be conversation ID or user ID)
        self.current_session: Optional[str] = None

    def write_turn(self, role:str, content:str, metadata:Optional[dict]=None) -> None:
        """
        Record a conversation turn (with role and content). Stores in S, M, L tiers and annotates status.
        """
        if metadata is None:
            metadata = {}
        # Determine session (conversation) ID from metadata or use a default
        session_id = metadata.get("session_id") or metadata.get("conv_id") or "default"
        self.current_session = session_id

        # Automatic annotation of the turn status
        status = self._annotate_status(role, content)
        metadata['status'] = status
        metadata['role'] = role  # store role for context reconstruction

        # Create a MemoryItem for this turn
        mem_item = MemoryItem(content=content, metadata=dict(metadata))  # use copy of metadata
        # Store in session cache (S-tier) as part of conversation history list
        history = self.s_cache.get(session_id) or []
        history.append(mem_item)
        self.s_cache.put(session_id, history)

        # Store in short-term buffer (M-tier) for immediate context (as plain text)
        # Use an incrementing key or timestamp to preserve order
        key = f"{session_id}-{len(history)}"
        self.m_buffer.put(key, content)  # MBuffer will evict old entries if over capacity

        # (Optional) Store in long-term vector (L-tier) for archival or retrieval.
        # For example, store user messages under a user-specific key for long-term memory.
        if 'user_id' in metadata:
            user_key = f"user:{metadata['user_id']}"
            self.l_vector.put(user_key, mem_item)
        # Could also store all turns in LVector if long-term archival is desired:
        # self.l_vector.put(f"turn:{session_id}-{len(history)}", mem_item)

    def get_context_for_scope(self, scope:str, key:Optional[str]=None,
                              query_text:Optional[str]=None, filters:Optional[dict]=None) -> List[MemoryItem]:
        """
        Retrieve context (list of MemoryItem) relevant to the given scope and key.
        Supports filtering out ERR/WARN entries and compresses context if necessary.
        """
        result: List[MemoryItem] = []
        filters = filters or {}
        if scope == "task":
            # For task scope, use conversation history from SCache by conversation (session) ID
            conv_id = key or self.current_session or "default"
            history: List[MemoryItem] = self.s_cache.get(conv_id) or []
            # Apply filters: exclude ERR/WARN if requested
            filtered_history = [
                item for item in history
                if not (filters.get("exclude_err") and item.metadata.get("status") == "ERR")
                and not (filters.get("exclude_warn") and item.metadata.get("status") == "WARN")
            ]
            # Apply compression to the filtered history
            compressed_history = self._compress_history(filtered_history)
            result = compressed_history
        elif scope == "user":
            # For user scope, retrieve long-term memory by user ID (key is user id)
            if key:
                user_items = self.l_vector.get(f"user:{key}")
                if user_items:
                    # If stored as a single MemoryItem or list, normalize to list
                    result = user_items if isinstance(user_items, list) else [user_items]
        elif scope == "topic":
            # For topic scope, we could perform a vector search or retrieval using query_text
            # (Placeholder: not implemented, as retriever integration is not provided)
            result = []
        else:
            # default: return recent short-term context from MBuffer (last N messages)
            result_texts: List[str] = [entry["value"] for entry in self.m_buffer.data.values()]
            # Convert to MemoryItem list (with unknown roles, assume user/assistant alternation if needed)
            result = [MemoryItem(content=txt, metadata={}) for txt in result_texts]

        return result

    def dump_memory(self) -> List[dict]:
        """
        Export the entire memory content for debugging.
        Returns a list of dicts for each session in SCache with their messages.
        """
        all_sessions = []
        for sess_id, history in list(self.s_cache.data.items()):
            # Each history entry is MemoryItem; convert to dict for clarity
            sess_dump = {
                "session_id": sess_id,
                "turns": [
                    {"role": item.metadata.get("role"),
                     "content": item.content,
                     "status": item.metadata.get("status")}
                    for item in history["value"]  # SCache stores {"value": history_list, "ts": ...}
                ]
            }
            all_sessions.append(sess_dump)
        return all_sessions

    def _annotate_status(self, role:str, content:str) -> str:
        """Heuristically determine status of a message: OK, WARN, or ERR."""
        if role.lower() == "assistant":
            text = content.lower()
            if any(phrase in text for phrase in ["sorry", "cannot", "unable to"]):
                # Likely a refusal or safe-completion
                return "WARN"
            if "error" in text or "exception" in text or "traceback" in text:
                # Contains an error message or stack trace
                return "ERR"
            return "OK"
        # For user or other roles, we generally mark as OK (assuming input is valid)
        return "OK"

    def _compress_history(self, history: List[MemoryItem]) -> List[MemoryItem]:
        """
        Compress context by removing redundant tokens and applying simple diff compression.
        Returns a possibly reduced list of MemoryItem.
        """
        if not history:
            return history
        # If number of items exceeds 50, drop older ones (basic retention policy)
        if len(history) > 50:
            history = history[-50:]
        # Token-level deduplication across adjacent messages (remove exact overlaps at boundaries)
        compressed: List[MemoryItem] = [history[0]]
        for prev_item, curr_item in zip(history[:-1], history[1:]):
            prev_text = prev_item.content
            curr_text = curr_item.content
            # Remove duplicate trailing tokens from prev or leading tokens from curr
            overlap = _common_overlap(prev_text, curr_text)
            if overlap:
                # Replace the overlapping part in curr_text with a placeholder or remove it
                curr_text = curr_text[len(overlap):].lstrip()
            # Reconstruct MemoryItem for curr with updated content
            new_item = MemoryItem(content=curr_text, metadata=dict(curr_item.metadata))
            compressed.append(new_item)
        return compressed

# Helper function for compression: find common overlap between end of text1 and start of text2
def _common_overlap(text1: str, text2: str) -> str:
    max_overlap = ""
    min_len = min(len(text1), len(text2))
    # Check suffix of text1 against prefix of text2 for largest overlap
    for length in range(min_len, 0, -1):
        if text1.endswith(text2[:length]):
            max_overlap = text2[:length]
            break
    return max_overlap