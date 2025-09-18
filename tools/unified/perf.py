from __future__ import annotations

import time
from typing import Dict, Any, List


class PerfTracker:
    def __init__(self) -> None:
        self.records: List[Dict[str, Any]] = []

    def timeit(self):  # pragma: no cover (tiny wrapper)
        start = time.perf_counter()
        def done(success: bool, name: str = "op"):
            dur = time.perf_counter() - start
            self.records.append({"name": name, "success": success, "duration_s": dur})
            return dur
        return done

    def record(self, name: str, success: bool, duration_s: float) -> None:
        self.records.append({"name": name, "success": success, "duration_s": duration_s})

