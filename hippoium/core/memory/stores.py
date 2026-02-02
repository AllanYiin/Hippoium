from __future__ import annotations
"""In-memory cache implementations for S/M/L tiers and ColdStore.

Policies:
    - Eviction: FIFO capacity eviction across all tiers.
    - TTL: Lazy eviction on access and put, using an injectable clock.
    - Oversize (MBuffer): reject single entries exceeding max_tokens.
    - Namespace: optional key prefixing for session/user isolation.
"""

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any, Iterable, Protocol

from hippoium.ports.port_types import MemTier
from hippoium.ports.protocols import CacheProtocol
from hippoium.core.utils.token_counter import count_tokens


class Clock(Protocol):
    def now(self) -> datetime: ...


class RealClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


def build_namespaced_key(namespace: str | None, key: str) -> str:
    if namespace:
        return f"{namespace}:{key}"
    return key


@dataclass(frozen=True)
class VectorEntry:
    vector: list[float]
    payload: Any


def cosine_similarity(vec1: Iterable[float], vec2: Iterable[float]) -> float:
    a = list(vec1)
    b = list(vec2)
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    denom = (norm_a * norm_b) or 1e-8
    return float(dot / denom)


class SCache(CacheProtocol):
    """Session-level cache with optional TTL and capacity."""

    tier = MemTier.S

    def __init__(
        self,
        capacity: int | None = None,
        ttl: timedelta | None = timedelta(minutes=30),
        clock: "Clock | None" = None,
        namespace: str | None = None,
    ):
        self.capacity = capacity
        self.ttl = ttl
        self.clock = clock or RealClock()
        self.namespace = namespace
        self.data: OrderedDict[str, dict] = OrderedDict()
        self._lock = RLock()

    def _expired(self, ts: datetime, ttl: timedelta | None) -> bool:
        return bool(ttl and ts + ttl < self.clock.now())

    def get(self, key: str) -> Any | None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            item = self.data.get(namespaced)
            if not item:
                return None
            if self._expired(item["ts"], item.get("ttl", self.ttl)):
                del self.data[namespaced]
                return None
            return item["value"]

    def _evict_expired(self) -> None:
        if not self.ttl:
            return
        expired = []
        for k, item in self.data.items():
            if self._expired(item["ts"], item.get("ttl", self.ttl)):
                expired.append(k)
        for k in expired:
            del self.data[k]

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        now = self.clock.now()
        ttl_delta = timedelta(seconds=ttl) if ttl else None
        with self._lock:
            self._evict_expired()
            if namespaced in self.data:
                self.data[namespaced]["value"] = value
                self.data[namespaced]["ts"] = now
                if ttl_delta is not None:
                    self.data[namespaced]["ttl"] = ttl_delta
                return
            if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
                self.data.popitem(last=False)
            payload = {"value": value, "ts": now}
            if ttl_delta is not None:
                payload["ttl"] = ttl_delta
            self.data[namespaced] = payload

    def delete(self, key: str) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if namespaced in self.data:
                del self.data[namespaced]


class MBuffer(CacheProtocol):
    """Short-term buffer with message count and token limits.

    Oversize policy:
        If a single message exceeds ``max_tokens``, the put is rejected with a
        ``ValueError`` so callers can handle the oversize payload explicitly.
    """

    tier = MemTier.M

    def __init__(
        self,
        max_messages: int | None = None,
        max_tokens: int | None = None,
        ttl: timedelta | None = timedelta(minutes=30),
        clock: "Clock | None" = None,
        namespace: str | None = None,
    ):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.ttl = ttl
        self.clock = clock or RealClock()
        self.namespace = namespace
        self.data: OrderedDict[str, dict] = OrderedDict()
        self._token_count: int = 0
        self._lock = RLock()

    def _expired(self, ts: datetime, ttl: timedelta | None) -> bool:
        return bool(ttl and ts + ttl < self.clock.now())

    def get(self, key: str) -> Any | None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            item = self.data.get(namespaced)
            if not item:
                return None
            if self._expired(item["ts"], item.get("ttl", self.ttl)):
                self._token_count -= item["len"]
                del self.data[namespaced]
                return None
            return item["value"]

    def _evict_expired(self) -> None:
        if not self.ttl:
            return
        expired = []
        for k, item in self.data.items():
            if self._expired(item["ts"], item.get("ttl", self.ttl)):
                expired.append((k, item["len"]))
        for k, length in expired:
            del self.data[k]
            self._token_count -= length

    def _evict_count(self) -> None:
        if self.max_messages is not None and self.max_messages > 0:
            while len(self.data) >= self.max_messages:
                _, val = self.data.popitem(last=False)
                self._token_count -= val["len"]

    def _evict_tokens(self, new_len: int) -> None:
        if self.max_tokens is not None and self.max_tokens > 0:
            while self._token_count + new_len > self.max_tokens and len(self.data) > 0:
                _, val = self.data.popitem(last=False)
                self._token_count -= val["len"]

    def put(self, key: str, value: str, ttl: int | None = None) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        now = self.clock.now()
        new_len = count_tokens(value)
        if self.max_tokens is not None and self.max_tokens > 0 and new_len > self.max_tokens:
            raise ValueError("Message token count exceeds max_tokens limit")
        ttl_delta = timedelta(seconds=ttl) if ttl else None
        with self._lock:
            self._evict_expired()
            if namespaced in self.data:
                old = self.data[namespaced]
                self._token_count -= old["len"]
                del self.data[namespaced]
            self._evict_count()
            self._evict_tokens(new_len)
            payload = {"value": value, "ts": now, "len": new_len}
            if ttl_delta is not None:
                payload["ttl"] = ttl_delta
            self.data[namespaced] = payload
            self._token_count += new_len

    def delete(self, key: str) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if namespaced in self.data:
                self._token_count -= self.data[namespaced]["len"]
                del self.data[namespaced]


class LVector(CacheProtocol):
    """Long-term vector store (FIFO capacity control + cosine similarity search)."""

    tier = MemTier.L

    def __init__(self, capacity: int | None = None, namespace: str | None = None):
        self.capacity = capacity
        self.namespace = namespace
        self.data: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            return self.data.get(namespaced)

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
                self.data.popitem(last=False)
            self.data[namespaced] = value

    def put_vector(self, key: str, vector: list[float], payload: Any) -> None:
        self.put(key, VectorEntry(vector=vector, payload=payload))

    def add(self, key: str, vector: list[float], payload: Any) -> None:
        self.put_vector(key, vector, payload)

    def similarity_search(self, query_vector: Iterable[float], top_k: int = 5) -> list[tuple[str, Any, float]]:
        scored: list[tuple[str, Any, float]] = []
        with self._lock:
            for key, value in self.data.items():
                if isinstance(value, VectorEntry):
                    score = cosine_similarity(query_vector, value.vector)
                    scored.append((key, value.payload, score))
        scored.sort(key=lambda item: item[2], reverse=True)
        return scored[:top_k]

    def delete(self, key: str) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if namespaced in self.data:
                del self.data[namespaced]


class ColdStore(CacheProtocol):
    """Cold storage – unlimited by default."""

    tier = MemTier.COLD

    def __init__(self, capacity: int | None = None, namespace: str | None = None):
        self.capacity = capacity
        self.namespace = namespace
        self.data: OrderedDict[str, Any] = OrderedDict()
        self._lock = RLock()

    def get(self, key: str) -> Any | None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            return self.data.get(namespaced)

    def put(self, key: str, value: Any, ttl: int | None = None) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
                self.data.popitem(last=False)
            self.data[namespaced] = value

    def delete(self, key: str) -> None:
        namespaced = build_namespaced_key(self.namespace, key)
        with self._lock:
            if namespaced in self.data:
                del self.data[namespaced]
