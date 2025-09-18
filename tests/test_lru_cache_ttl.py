from utils.lru_cache_ttl import LruCacheTtl
import time


def test_lru_cache_ttl_basic():
    c = LruCacheTtl(capacity=2, ttl_s=0.05)
    c.put("a", 1)
    assert c.get("a") == 1
    time.sleep(0.06)
    assert c.get("a") is None


def test_lru_cache_ttl_eviction():
    c = LruCacheTtl(capacity=2, ttl_s=10)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    # a should be evicted
    assert c.get("a") is None and c.get("b") == 2 and c.get("c") == 3

