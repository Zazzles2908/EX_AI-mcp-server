from __future__ import annotations

from typing import List


class RoundRobinBalancer:
    def __init__(self, endpoints: List[str]) -> None:
        if not endpoints:
            raise ValueError("endpoints required")
        self.endpoints = list(endpoints)
        self._i = 0

    def next(self) -> str:
        ep = self.endpoints[self._i % len(self.endpoints)]
        self._i += 1
        return ep

