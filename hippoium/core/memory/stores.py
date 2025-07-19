"""
Simple in-memory store implementations for each tier.
"""
from __future__ import annotations
from collections import OrderedDict
from typing import Any
from hippoium.ports.types import MemTier
from hippoium.core.utils.hasher import hash_text


class _BaseStore:
    def __init__(self, capacity: int | None = None):
        self.capacity = capacity
        self.data: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str):
        return self.data.get(key)

    def put(self, key: str, value):
        if self.capacity and len(self.data) >= self.capacity:
            self.data.popitem(last=False)  # FIFO eviction
        self.data[key] = value

    def __len__(self):
        return len(self.data)


class SCache(_BaseStore):
    tier = MemTier.S


class MBuffer(_BaseStore):
    tier = MemTier.M


class LVector(_BaseStore):
    tier = MemTier.L


class ColdStore(_BaseStore):
    tier = MemTier.COLD
