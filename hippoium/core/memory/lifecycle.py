"""
Lifecycle manager – TTL & rollback helpers for memory tiers.
"""
from __future__ import annotations
from datetime import timedelta

from hippoium.ports.port_types import MemTier
from hippoium.core.memory.stores import Clock, RealClock, SCache, MBuffer, LVector, ColdStore


class LifecycleManager:
    def __init__(self, scache: SCache, m: MBuffer, l: LVector, clock: Clock | None = None):
        self.s, self.m, self.l = scache, m, l
        self.ttl = timedelta(minutes=30)
        self.clock = clock or getattr(scache, "clock", RealClock())

    def sweep(self):
        now = self.clock.now()
        for store in (self.s, self.m):
            with store._lock:
                expired = []
                for k, v in store.data.items():
                    if v["ts"] + self.ttl < now:
                        expired.append(k)
                for k in expired:
                    if isinstance(store, MBuffer):
                        store._token_count -= store.data[k]["len"]
                    del store.data[k]

    def promote(self, key: str):
        """Promote hot item from MBuffer → LVector."""
        with self.m._lock:
            if key in self.m.data:
                self.l.put(key, self.m.get(key))
