from __future__ import annotations

"""In-memory cache implementations for S/M/L tiers and ColdStore."""

from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

from hippoium.ports.port_types import MemTier
from hippoium.ports.protocols import CacheProtocol
from hippoium.core.utils.token_counter import count_tokens


class SCache(CacheProtocol):
    """Session-level cache with optional TTL and capacity."""

    tier = MemTier.S

    def __init__(self, capacity: int | None = None, ttl: timedelta | None = timedelta(minutes=30)):
        self.capacity = capacity
        self.ttl = ttl
        self.data: OrderedDict[str, dict] = OrderedDict()

    def _expired(self, ts: datetime) -> bool:
        return bool(self.ttl and ts + self.ttl < datetime.utcnow())

    def get(self, key: str) -> Any | None:
        item = self.data.get(key)
        if not item:
            return None
        if self._expired(item["ts"]):
            del self.data[key]
            return None
        return item["value"]

    def put(self, key: str, value: Any) -> None:
        now = datetime.utcnow()
        if key in self.data:
            self.data[key]["value"] = value
            self.data[key]["ts"] = now
            return
        if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
            self.data.popitem(last=False)
        self.data[key] = {"value": value, "ts": now}

    def delete(self, key: str) -> None:
        if key in self.data:
            del self.data[key]


class MBuffer(CacheProtocol):
    """Short-term buffer with message count and token limits."""

    tier = MemTier.M

    def __init__(self, max_messages: int | None = None, max_tokens: int | None = None,
                 ttl: timedelta | None = timedelta(minutes=30)):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.ttl = ttl
        self.data: OrderedDict[str, dict] = OrderedDict()
        self._token_count: int = 0

    def _expired(self, ts: datetime) -> bool:
        return bool(self.ttl and ts + self.ttl < datetime.utcnow())

    def get(self, key: str) -> Any | None:
        item = self.data.get(key)
        if not item:
            return None
        if self._expired(item["ts"]):
            self._token_count -= item["len"]
            del self.data[key]
            return None
        return item["value"]

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

    def put(self, key: str, value: str) -> None:
        now = datetime.utcnow()
        new_len = count_tokens(value)
        if key in self.data:
            old = self.data[key]
            self._token_count -= old["len"]
            del self.data[key]
        self._evict_count()
        self._evict_tokens(new_len)
        self.data[key] = {"value": value, "ts": now, "len": new_len}
        self._token_count += new_len

    def delete(self, key: str) -> None:
        if key in self.data:
            self._token_count -= self.data[key]["len"]
            del self.data[key]


class LVector(CacheProtocol):
    """Long-term vector store (simple FIFO capacity control)."""

    tier = MemTier.L

    def __init__(self, capacity: int | None = None):
        self.capacity = capacity
        self.data: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        return self.data.get(key)

    def put(self, key: str, value: Any) -> None:
        if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
            self.data.popitem(last=False)
        self.data[key] = value

    def delete(self, key: str) -> None:
        if key in self.data:
            del self.data[key]


class ColdStore(CacheProtocol):
    """Cold storage – unlimited by default."""

    tier = MemTier.COLD

    def __init__(self, capacity: int | None = None):
        self.capacity = capacity
        self.data: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str) -> Any | None:
        return self.data.get(key)

    def put(self, key: str, value: Any) -> None:
        if self.capacity is not None and self.capacity > 0 and len(self.data) >= self.capacity:
            self.data.popitem(last=False)
        self.data[key] = value

    def delete(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
