"""
Tiered cache gateway – routes get/put to S/M/L/COLD stores.
"""
from hippoium.ports.types import MemTier
from hippoium.core.memory.stores import SCache, MBuffer, LVector, ColdStore


class TierCache:
    def __init__(self, s: SCache, m: MBuffer, l: LVector, cold: ColdStore):
        self._map = {
            MemTier.S: s,
            MemTier.M: m,
            MemTier.L: l,
            MemTier.COLD: cold,
        }

    def get(self, key: str, tier: MemTier):
        return self._map[tier].get(key)

    def put(self, key: str, value, tier: MemTier):
        self._map[tier].put(key, value)
