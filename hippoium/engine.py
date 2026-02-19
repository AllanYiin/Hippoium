from concurrent.futures import Future, ThreadPoolExecutor
from datetime import timedelta
from threading import Event, RLock, Thread
from typing import Optional

from hippoium.core.cer.compressor import Compressor

# assuming stores.py defines SCache, MBuffer, LVector
from hippoium.core.memory import stores
from hippoium.core.memory.stores import build_namespaced_key
from hippoium.core.utils.hasher import hash_text_sha256
from hippoium.ports.domain import MemoryItem
from hippoium.ports.protocols import ContextEngineProtocol


class DefaultContextEngine(ContextEngineProtocol):
    """
    Default implementation of ContextEngineProtocol that manages S/M/L memory tiers
    and handles conversation record input processing.
    """
    def __init__(
        self,
        max_messages: int = 50,
        max_tokens: int = 2048,
        session_ttl: Optional[timedelta] = timedelta(minutes=30),
        compression_debug: bool = False,
        compression_preview_chars: int = 80,
        enable_background_workers: bool = False,
        housekeeping_interval_seconds: float = 30.0,
    ):
        # S-tier: session cache (stores entire conversation history by session ID)
        self.s_cache = stores.SCache(ttl=session_ttl)
        # M-tier: short-term buffer (recent messages with limits)
        self.m_buffer = stores.MBuffer(max_messages=max_messages, max_tokens=max_tokens)
        # L-tier: long-term vector store (archive or knowledge base)
        self.l_vector = stores.LVector(capacity=None)
        # Track current session ID for context (could be conversation ID or user ID)
        self.current_session: Optional[str] = None
        self.compression_debug = compression_debug
        self.compression_preview_chars = compression_preview_chars
        self.enable_background_workers = enable_background_workers
        self.housekeeping_interval_seconds = max(housekeeping_interval_seconds, 1.0)

        self._memory_executor: ThreadPoolExecutor | None = None
        self._compression_executor: ThreadPoolExecutor | None = None
        self._housekeeping_executor: ThreadPoolExecutor | None = None
        self._housekeeping_stop = Event()
        self._housekeeping_thread: Thread | None = None
        self._compression_lock = RLock()
        self._compression_cache: dict[str, list[MemoryItem]] = {}
        self._compression_jobs: dict[str, Future[list[MemoryItem]]] = {}
        self._compression_fingerprints: dict[str, tuple[str, ...]] = {}

        if self.enable_background_workers:
            self._memory_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hippo-memory")
            self._compression_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hippo-compression")
            self._housekeeping_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hippo-housekeeping")
            self._housekeeping_thread = Thread(target=self._housekeeping_loop, daemon=True)
            self._housekeeping_thread.start()

    def close(self) -> None:
        """釋放背景執行緒資源，避免測試或程序結束時殘留 worker。"""
        self._housekeeping_stop.set()
        if self._housekeeping_thread and self._housekeeping_thread.is_alive():
            self._housekeeping_thread.join(timeout=1.0)
        for executor in (self._memory_executor, self._compression_executor, self._housekeeping_executor):
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)

    def __del__(self) -> None:
        self.close()

    def write_turn(
        self,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Record a conversation turn (with role and content). Stores in S, M, L tiers
        and annotates status.
        """
        if metadata is None:
            metadata = {}
        if self.enable_background_workers and self._memory_executor is not None:
            self._memory_executor.submit(self._write_turn_sync, role, content, dict(metadata))
            return
        self._write_turn_sync(role, content, dict(metadata))

    def _write_turn_sync(self, role: str, content: str, metadata: dict) -> None:
        # Determine session (conversation) ID from metadata or use a default
        session_id = metadata.get("session_id") or metadata.get("conv_id") or "default"
        self.current_session = session_id

        status = self._annotate_status(role, content)
        metadata["status"] = status
        metadata["role"] = role

        mem_item = MemoryItem(content=content, metadata=dict(metadata))
        history = self.s_cache.get(session_id) or []
        history.append(mem_item)
        self.s_cache.put(session_id, history)

        key = build_namespaced_key(session_id, str(len(history)))
        self.m_buffer.put(key, content)

        if "user_id" in metadata:
            user_key = build_namespaced_key("user", str(metadata["user_id"]))
            self.l_vector.put(user_key, mem_item)

    def get_context_for_scope(
        self,
        scope: str,
        key: Optional[str] = None,
        query_text: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[MemoryItem]:
        """
        Retrieve context (list of MemoryItem) relevant to the given scope and key.
        Supports filtering out ERR/WARN entries and compresses context if necessary.
        """
        result: list[MemoryItem] = []
        filters = filters or {}
        if scope == "task":
            # For task scope, use conversation history from SCache by conversation
            # (session) ID.
            conv_id = key or self.current_session or "default"
            history: list[MemoryItem] = self.s_cache.get(conv_id) or []
            # Apply filters: exclude ERR/WARN if requested
            filtered_history = [
                item for item in history
                if not (
                    filters.get("exclude_err")
                    and item.metadata.get("status") == "ERR"
                )
                and not (
                    filters.get("exclude_warn")
                    and item.metadata.get("status") == "WARN"
                )
            ]
            if self.enable_background_workers and self._compression_executor is not None:
                result = self._get_task_scope_context_async(conv_id, filtered_history)
            else:
                result = self._compress_history(filtered_history)
        elif scope == "user":
            # For user scope, retrieve long-term memory by user ID (key is user id)
            if key:
                user_items = self.l_vector.get(build_namespaced_key("user", str(key)))
                if user_items:
                    # If stored as a single MemoryItem or list, normalize to list
                    result = (
                        user_items
                        if isinstance(user_items, list)
                        else [user_items]
                    )
        elif scope == "topic":
            # For topic scope, we could perform a vector search or retrieval using
            # query_text.
            # (Placeholder: not implemented, as retriever integration is not provided)
            result = []
        else:
            # default: return recent short-term context from MBuffer (last N messages)
            with self.m_buffer._lock:
                result_texts: list[str] = [
                    entry["value"] for entry in self.m_buffer.data.values()
                ]
            # Convert to MemoryItem list (with unknown roles, assume user/assistant
            # alternation if needed).
            result = [MemoryItem(content=txt, metadata={}) for txt in result_texts]

        return result

    def _get_task_scope_context_async(self, conv_id: str, filtered_history: list[MemoryItem]) -> list[MemoryItem]:
        fingerprint = tuple(item.content for item in filtered_history)
        with self._compression_lock:
            cached = self._compression_cache.get(conv_id)
            cached_fingerprint = self._compression_fingerprints.get(conv_id)
            if cached is not None and cached_fingerprint == fingerprint:
                return cached

            pending = self._compression_jobs.get(conv_id)
            if pending is None or pending.done():
                self._compression_jobs[conv_id] = self._compression_executor.submit(
                    self._compress_for_session,
                    conv_id,
                    filtered_history,
                    fingerprint,
                )

        # 非阻塞：若背景壓縮尚未完成，直接回傳裁切後內容以避免卡住 UI。
        return filtered_history[-50:] if len(filtered_history) > 50 else filtered_history

    def _compress_for_session(
        self,
        conv_id: str,
        history: list[MemoryItem],
        fingerprint: tuple[str, ...],
    ) -> list[MemoryItem]:
        compressed = self._compress_history(history)
        with self._compression_lock:
            self._compression_cache[conv_id] = compressed
            self._compression_fingerprints[conv_id] = fingerprint
            self._compression_jobs.pop(conv_id, None)
        return compressed

    def _housekeeping_loop(self) -> None:
        while not self._housekeeping_stop.wait(self.housekeeping_interval_seconds):
            if self._housekeeping_executor is None:
                continue
            self._housekeeping_executor.submit(self._run_housekeeping)

    def _run_housekeeping(self) -> None:
        with self.s_cache._lock:
            self.s_cache._evict_expired()
        with self.m_buffer._lock:
            self.m_buffer._evict_expired()

    def dump_memory(self) -> list[dict]:
        """
        Export the entire memory content for debugging.
        Returns a list of dicts for each session in SCache with their messages.
        """
        all_sessions = []
        with self.s_cache._lock:
            sessions = list(self.s_cache.data.items())
        for sess_id, history in sessions:
            # Each history entry is MemoryItem; convert to dict for clarity
            sess_dump = {
                "session_id": sess_id,
                "turns": [
                    {"role": item.metadata.get("role"),
                     "content": item.content,
                     "status": item.metadata.get("status")}
                    for item in history["value"]
                    # SCache stores {"value": ..., "ts": ...}
                ]
            }
            all_sessions.append(sess_dump)
        return all_sessions

    def _annotate_status(self, role: str, content: str) -> str:
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

    def _compress_history(self, history: list[MemoryItem]) -> list[MemoryItem]:
        """利用 Compressor 模組進行 Hash 去重與 Diff-Patch 壓縮。"""
        if not history:
            return history
        if len(history) > 50:
            history = history[-50:]

        texts = [item.content for item in history]
        compressor = Compressor()
        compressed_texts = compressor.compress(texts)
        compressed_items: list[MemoryItem] = []
        for item, new_text in zip(history, compressed_texts):
            new_meta = dict(item.metadata or {})
            original_text = item.content
            original_hash = hash_text_sha256(original_text)
            new_meta["compressed"] = True
            new_meta["compression_method"] = {
                "dedup": compressor.dedup_strategy.name.lower(),
                "trim": compressor.trim_policy.name.lower(),
            }
            new_meta["compression_ref"] = {
                "sha256": original_hash,
                "length": len(original_text),
                "stored_in": "S-Cache",
            }
            new_meta["compression_result"] = {
                "length": len(new_text),
            }
            if self.compression_debug:
                preview = self.compression_preview_chars
                new_meta["compression_debug"] = {
                    "original_preview": original_text[:preview],
                    "compressed_preview": new_text[:preview],
                }
            compressed_items.append(MemoryItem(content=new_text, metadata=new_meta))
        return compressed_items

# Helper function for compression: find common overlap between end of text1
# and start of text2.
def _common_overlap(text1: str, text2: str) -> str:
    max_overlap = ""
    min_len = min(len(text1), len(text2))
    # Check suffix of text1 against prefix of text2 for largest overlap
    for length in range(min_len, 0, -1):
        if text1.endswith(text2[:length]):
            max_overlap = text2[:length]
            break
    return max_overlap
