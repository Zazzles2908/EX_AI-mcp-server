from __future__ import annotations

from typing import Sequence
from monitoring.autoscale import should_scale_up, should_scale_down


class WorkerPool:
    def __init__(self, min_workers: int = 1, max_workers: int = 10, current_workers: int = 1) -> None:
        self.min_workers = min_workers
        self.max_workers = max_workers
        self.current_workers = current_workers

    def decide(self, queue_depths: Sequence[int], avg_latency_ms: float) -> str:
        if should_scale_up(queue_depths, avg_latency_ms, self.max_workers, self.current_workers):
            self.current_workers = min(self.max_workers, self.current_workers + 1)
            return "scale_up"
        if should_scale_down(queue_depths, avg_latency_ms, self.min_workers, self.current_workers):
            self.current_workers = max(self.min_workers, self.current_workers - 1)
            return "scale_down"
        return "hold"

