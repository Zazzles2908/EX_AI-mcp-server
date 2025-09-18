from __future__ import annotations

from collections import deque
from typing import Deque, Tuple


class HealthTrendStore:
    """In-memory rolling metrics with basic degrade detection."""

    def __init__(self, window: int = 5, threshold: float = 0.8) -> None:
        self.window = window
        self.threshold = threshold
        self.values: Deque[float] = deque(maxlen=window)

    def add_metric(self, value: float) -> None:
        self.values.append(float(value))

    def average(self) -> float:
        return sum(self.values) / len(self.values) if self.values else 1.0

    def is_degrading(self) -> bool:
        if len(self.values) < self.window:
            return False
        return self.average() < self.threshold

