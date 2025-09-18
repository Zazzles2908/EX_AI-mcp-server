from __future__ import annotations

from typing import Sequence


def should_scale_up(queue_depths: Sequence[int], avg_latency_ms: float, max_workers: int, current_workers: int) -> bool:
    if current_workers >= max_workers:
        return False
    pending = sum(queue_depths)
    return pending > current_workers * 5 or avg_latency_ms > 1500


def should_scale_down(queue_depths: Sequence[int], avg_latency_ms: float, min_workers: int, current_workers: int) -> bool:
    if current_workers <= min_workers:
        return False
    pending = sum(queue_depths)
    return pending < (current_workers - 1) * 2 and avg_latency_ms < 500

