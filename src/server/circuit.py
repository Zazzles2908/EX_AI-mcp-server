"""
Simple circuit breaker for provider-level health guarding.
P1 scope: in-memory, process-local only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class _State:
    failures: int = 0
    successes: int = 0
    opened_at: float | None = None


class CircuitBreakers:
    def __init__(self):
        self._states: Dict[str, _State] = {}

    def _get(self, key: str) -> _State:
        st = self._states.get(key)
        if not st:
            st = _State()
            self._states[key] = st
        return st

    def allow(self, key: str, *, failure_threshold: int = 3, cooloff_seconds: int = 60) -> bool:
        st = self._get(key)
        if st.opened_at is None:
            return True
        # half-open after cooloff
        if (time.time() - st.opened_at) >= cooloff_seconds:
            return True
        return False

    def record_success(self, key: str, *, success_reset: int = 2):
        st = self._get(key)
        st.successes += 1
        # Close circuit after a few successes when half-open
        if st.opened_at is not None and st.successes >= success_reset:
            st.opened_at = None
            st.failures = 0

    def record_failure(self, key: str, *, failure_threshold: int = 3):
        st = self._get(key)
        st.failures += 1
        st.successes = 0
        if st.failures >= failure_threshold:
            st.opened_at = time.time()


# Singleton instance
circuit = CircuitBreakers()

