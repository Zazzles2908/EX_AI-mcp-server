from __future__ import annotations

import time
from typing import Dict, Any, List


class Counter:
    def __init__(self, name: str) -> None:
        self.name = name
        self.value = 0

    def inc(self, n: int = 1) -> None:
        self.value += n


class Timer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.durations: List[float] = []

    def timeit(self):
        start = time.perf_counter()
        def done():
            self.durations.append(time.perf_counter() - start)
        return done

    def avg(self) -> float:
        return sum(self.durations) / len(self.durations) if self.durations else 0.0


class MetricsSink:
    def __init__(self) -> None:
        self.counters: Dict[str, Counter] = {}
        self.timers: Dict[str, Timer] = {}

    def counter(self, name: str) -> Counter:
        if name not in self.counters:
            self.counters[name] = Counter(name)
        return self.counters[name]

    def timer(self, name: str) -> Timer:
        if name not in self.timers:
            self.timers[name] = Timer(name)
        return self.timers[name]

