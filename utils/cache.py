"""
Memory-only LRU + TTL cache for session continuity.
Default-safe: enabled only when called; no external dependencies.

Env (documented):
- CACHE_BACKEND=memory|redis (only 'memory' implemented)
- CACHE_TTL_SEC=10800 (3 hours)
- CACHE_MAX_ITEMS=1000
- REDIS_URL=... (reserved for future)
"""
from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

DEFAULT_TTL = int(os.getenv("CACHE_TTL_SEC", "10800") or "10800")
DEFAULT_MAX_ITEMS = int(os.getenv("CACHE_MAX_ITEMS", "1000") or "1000")


@dataclass
class _Entry:
    value: Any
    expires_at: float
    prev: Optional[str] = None
    next: Optional[str] = None


class MemoryLRUTTL:
    """Simple LRU with TTL. Not multiprocessing-safe; fine for stdio server.
    Thread-safe via a single lock.
    """

    def __init__(self, max_items: int = DEFAULT_MAX_ITEMS, ttl_sec: int = DEFAULT_TTL) -> None:
        self.max_items = max_items
        self.ttl = ttl_sec
        self._lock = threading.RLock()
        self._data: Dict[str, _Entry] = {}
        self._head: Optional[str] = None  # MRU
        self._tail: Optional[str] = None  # LRU

    def _evict_if_needed(self) -> None:
        while len(self._data) > self.max_items:
            # Evict LRU (tail)
            tail = self._tail
            if tail is None:
                return
            self._remove_key(tail)

    def _remove_key(self, key: str) -> None:
        entry = self._data.pop(key, None)
        if not entry:
            return
        # relink neighbors
        prev_k, next_k = entry.prev, entry.next
        if prev_k is not None:
            self._data[prev_k].next = next_k
        else:
            self._head = next_k
        if next_k is not None:
            self._data[next_k].prev = prev_k
        else:
            self._tail = prev_k

    def _move_to_head(self, key: str) -> None:
        if key == self._head:
            return
        entry = self._data.get(key)
        if not entry:
            return
        # unlink
        prev_k, next_k = entry.prev, entry.next
        if prev_k is not None:
            self._data[prev_k].next = next_k
        else:
            self._head = next_k
        if next_k is not None:
            self._data[next_k].prev = prev_k
        else:
            self._tail = prev_k
        # link at head
        entry.prev = None
        entry.next = self._head
        if self._head is not None:
            self._data[self._head].prev = key
        self._head = key
        if self._tail is None:
            self._tail = key

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if now >= entry.expires_at:
                self._remove_key(key)
                return None
            self._move_to_head(key)
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        exp = time.time() + (ttl if ttl is not None else self.ttl)
        with self._lock:
            if key in self._data:
                e = self._data[key]
                e.value = value
                e.expires_at = exp
                self._move_to_head(key)
            else:
                self._data[key] = _Entry(value=value, expires_at=exp, prev=None, next=self._head)
                if self._head is not None:
                    self._data[self._head].prev = key
                self._head = key
                if self._tail is None:
                    self._tail = key
            self._evict_if_needed()

    def stats(self) -> Tuple[int, int]:
        # (count, max_items)
        with self._lock:
            return (len(self._data), self.max_items)


# Singleton cache for sessions (safe default)
_session_cache = MemoryLRUTTL()

def get_session_cache() -> MemoryLRUTTL:
    return _session_cache


def make_session_key(continuation_id: str) -> str:
    return f"session:{continuation_id}"


__all__ = [
    "MemoryLRUTTL",
    "get_session_cache",
    "make_session_key",
]

