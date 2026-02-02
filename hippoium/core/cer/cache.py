"""
Tiered cache gateway – routes get/put to S/M/L/COLD stores.
"""
from datetime import timedelta
from typing import Any

from hippoium.ports.port_types import MemTier

from hippoium.ports.protocols import CacheProtocol
from hippoium.core.memory.stores import SCache, MBuffer, LVector, ColdStore


class TierCache:
    """Gateway managing multiple cache tiers."""

    def __init__(self, s: CacheProtocol, m: CacheProtocol, l: CacheProtocol, cold: CacheProtocol):
        self._map = {
            MemTier.S: s,
            MemTier.M: m,
            MemTier.L: l,
            MemTier.COLD: cold,
        }

    def get(self, key: str, tier: MemTier):
        return self._map[tier].get(key)

    def put(self, key: str, value, tier: MemTier, ttl: int | None = None):
        self._map[tier].put(key, value, ttl=ttl)

    def delete(self, key: str, tier: MemTier):
        self._map[tier].delete(key)

    @classmethod
    def from_config(cls, config: dict) -> "TierCache":
        """Instantiate tiered caches from a config dictionary."""

        def cfg(name: str) -> dict:
            return config.get(name, {}) if config else {}

        sc_cfg = cfg("SCache")
        if sc_cfg.get("enabled", True):
            s_obj = SCache(capacity=sc_cfg.get("capacity"), ttl=sc_cfg.get("ttl", timedelta(minutes=30)))
        else:
            s_obj = _NoopCache()

        mb_cfg = cfg("MBuffer")
        if mb_cfg.get("enabled", True):
            m_obj = MBuffer(max_messages=mb_cfg.get("max_messages"), max_tokens=mb_cfg.get("max_tokens"), ttl=mb_cfg.get("ttl", timedelta(minutes=30)))
        else:
            m_obj = _NoopCache()

        lv_cfg = cfg("LVector")
        if lv_cfg.get("enabled", True):
            l_obj = LVector(capacity=lv_cfg.get("capacity"))
        else:
            l_obj = _NoopCache()

        cs_cfg = cfg("ColdStore")
        if cs_cfg.get("enabled", True):
            cold_obj = ColdStore(capacity=cs_cfg.get("capacity"))
        else:
            cold_obj = _NoopCache()

        return cls(s_obj, m_obj, l_obj, cold_obj)


class _NoopCache(CacheProtocol):
    """Placeholder for disabled cache tier."""

    def get(self, key: str):
        return None

    def put(self, key: str, value: Any, ttl: int | None = None):
        pass

    def delete(self, key: str):
        pass
