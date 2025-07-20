"""
Lifecycle manager – TTL & rollback helpers for memory tiers.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from hippoium.ports.port_types import MemTier
from hippoium.core.memory.stores import SCache, MBuffer, LVector, ColdStore


class LifecycleManager:
    def __init__(self, scache: SCache, m: MBuffer, l: LVector):
        self.s, self.m, self.l = scache, m, l
        self.ttl = timedelta(minutes=30)

    def sweep(self):
        now = datetime.utcnow()
        for store in (self.s, self.m):
            expired = [k for k, v in store.data.items() if v["ts"] + self.ttl < now]
            for k in expired:
                del store.data[k]

    def promote(self, key: str):
        """Promote hot item from MBuffer → LVector."""
        if key in self.m.data:
            self.l.put(key, self.m.get(key))
