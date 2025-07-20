import time
from datetime import timedelta

from hippoium.core.cer.cache import TierCache
from hippoium.core.memory.stores import SCache, MBuffer, LVector, ColdStore
from hippoium.ports.port_types import MemTier


def test_scache_basic_ttl_and_capacity():
    sc = SCache(capacity=2, ttl=timedelta(seconds=1))
    sc.put("user", "Alice")
    sc.put("lang", "Python")
    assert sc.get("user") == "Alice"
    assert sc.get("lang") == "Python"
    sc.put("level", "beginner")
    assert sc.get("user") is None
    assert sc.get("lang") == "Python"
    assert sc.get("level") == "beginner"
    time.sleep(1.1)
    assert sc.get("lang") is None
    assert sc.get("level") is None


def test_mbuffer_eviction_by_count_and_tokens():
    mb = MBuffer(max_messages=3, max_tokens=5)
    mb.put("m1", "Hello")
    mb.put("m2", "world")
    mb.put("m3", "!")
    assert mb.get("m1") == "Hello"
    mb.put("m4", "New")
    assert mb.get("m1") is None
    assert mb.get("m2") == "world"
    long_text = "one two three four five six"
    mb.put("m5", long_text)
    assert mb.get("m5") == long_text
    assert all(mb.get(k) is None for k in ("m2", "m3", "m4"))


def test_mbuffer_ttl_expiry():
    mb = MBuffer(max_messages=5, max_tokens=100, ttl=timedelta(seconds=1))
    mb.put("x", "test")
    assert mb.get("x") == "test"
    time.sleep(1.1)
    assert mb.get("x") is None


def test_lvector_basic_and_capacity():
    lv = LVector(capacity=2)
    lv.put("k1", [1, 2, 3])
    lv.put("k2", [4, 5, 6])
    lv.put("k3", [7, 8, 9])
    assert lv.get("k1") is None
    assert lv.get("k2") == [4, 5, 6]
    assert lv.get("k3") == [7, 8, 9]


def test_coldstore_basic():
    cold = ColdStore(capacity=1)
    cold.put("a", "dataA")
    cold.put("b", "dataB")
    assert cold.get("a") is None
    assert cold.get("b") == "dataB"


def test_tiercache_integration():
    cfg = {
        "SCache": {"enabled": True, "capacity": 2, "ttl": timedelta(seconds=5)},
        "MBuffer": {"enabled": True, "max_messages": 2, "max_tokens": 10, "ttl": timedelta(minutes=5)},
        "LVector": {"enabled": False},
        "ColdStore": {"enabled": True}
    }
    tc = TierCache.from_config(cfg)
    tc.put("temp", "123", MemTier.S)
    assert tc.get("temp", MemTier.S) == "123"
    tc.put("summary1", "Short", MemTier.M)
    tc.put("summary2", "Another", MemTier.M)
    tc.put("summary3", "Third", MemTier.M)
    assert tc.get("summary1", MemTier.M) is None
    assert tc.get("summary2", MemTier.M) == "Another"
    assert tc.get("summary3", MemTier.M) == "Third"
    tc.put("vec1", [0.1, 0.2], MemTier.L)
    assert tc.get("vec1", MemTier.L) is None
    tc.put("archive", {"text": "old"}, MemTier.COLD)
    assert tc.get("archive", MemTier.COLD) == {"text": "old"}
