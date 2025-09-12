from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar
import time

T = TypeVar("T")


@dataclass
class RetryPolicy:
    retries: int = 3
    base_delay: float = 0.2
    max_delay: float = 2.0


class ResilientErrorHandler:
    """Simple retry/backoff/fallback scaffolding.

    No network calls; the execute method accepts callables to remain testable.
    """

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self.policy = policy or RetryPolicy()

    def execute(self, fn: Callable[[], T], fallback: Callable[[], T] | None = None) -> T:
        delay = self.policy.base_delay
        for attempt in range(self.policy.retries):
            try:
                return fn()
            except Exception:
                if attempt == self.policy.retries - 1:
                    if fallback is not None:
                        return fallback()
                    raise
                time.sleep(min(delay, self.policy.max_delay))
                delay *= 2
        # Unreachable, but for type checkers
        return fn()

