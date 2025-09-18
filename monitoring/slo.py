from __future__ import annotations

from typing import Dict


class SLO:
    def __init__(self, latency_p95_ms: int = 1000, success_rate: float = 0.99) -> None:
        self.latency_p95_ms = latency_p95_ms
        self.success_rate = success_rate

    def evaluate(self, metrics: Dict[str, float]) -> bool:
        lat = metrics.get("p95_ms", 0.0)
        succ = metrics.get("success_rate", 1.0)
        return (lat <= self.latency_p95_ms) and (succ >= self.success_rate)

