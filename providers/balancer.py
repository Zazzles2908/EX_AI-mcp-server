# DEPRECATION NOTE: Consider migrating to src/core/agentic/hybrid_platform_manager.py patterns.
# This file will be reviewed for Phase B/C; no behavior change in Phase A.

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

