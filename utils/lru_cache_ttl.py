from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Callable, Tuple


class LruCacheTtl:
    def __init__(self, capacity: int = 128, ttl_s: float = 60.0) -> None:
        self.capacity = capacity
        self.ttl_s = ttl_s
        self._data: "OrderedDict[Any, Tuple[float, Any]]" = OrderedDict()
        self._lock = RLock()

    def get(self, key: Any, loader: Callable[[], Any] | None = None) -> Any:
        now = time.time()
        with self._lock:
            if key in self._data:
                ts, val = self._data.pop(key)
                if now - ts <= self.ttl_s:
                    self._data[key] = (ts, val)
                    return val
            if loader is None:
                return None
            val = loader()
            self._data[key] = (now, val)
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)
            return val

    def put(self, key: Any, value: Any) -> None:
        with self._lock:
            self._data.pop(key, None)
            self._data[key] = (time.time(), value)
            if len(self._data) > self.capacity:
                self._data.popitem(last=False)

