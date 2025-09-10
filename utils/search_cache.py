"""Per-thread web search cache (LRU with TTL).

Cache key includes provider, locale, safety level, and normalized query.
"""
from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

DEFAULT_TTL = 300  # seconds
MAX_ENTRIES = 64   # small per-thread cache


def _now() -> float:
    return time.time()


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class LruTtlCache:
    def __init__(self, max_entries: int = MAX_ENTRIES):
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max = max_entries

    def get(self, key: str) -> Optional[Any]:
        now = _now()
        if key in self._data:
            entry = self._data.pop(key)
            if entry.expires_at >= now:
                # refresh LRU order
                self._data[key] = entry
                return entry.value
        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        now = _now()
        if key in self._data:
            self._data.pop(key)
        self._data[key] = CacheEntry(value=value, expires_at=now + ttl)
        # evict oldest
        while len(self._data) > self._max:
            self._data.popitem(last=False)


# Thread-bound caches indexed by thread_id
_THREAD_CACHES: Dict[str, LruTtlCache] = {}


def get_thread_cache(thread_id: str) -> LruTtlCache:
    c = _THREAD_CACHES.get(thread_id)
    if not c:
        c = LruTtlCache()
        _THREAD_CACHES[thread_id] = c
    return c


def make_key(provider: str, locale: str, safety: str, query: str) -> str:
    # Simple normalization
    qn = " ".join(query.lower().split()) if query else ""
    return f"{provider}|{locale}|{safety}|{qn}"

