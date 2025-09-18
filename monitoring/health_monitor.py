from __future__ import annotations

from typing import Dict, Callable


class HealthMonitor:
    """Aggregate multiple health signals into a single status.

    Each probe is a callable returning bool. All must be True for overall OK.
    """

    def __init__(self) -> None:
        self.probes: Dict[str, Callable[[], bool]] = {}

    def add_probe(self, name: str, fn: Callable[[], bool]) -> None:
        self.probes[name] = fn

    def status(self) -> Dict[str, bool]:
        results: Dict[str, bool] = {}
        for k, fn in self.probes.items():
            try:
                results[k] = bool(fn())
            except Exception:
                results[k] = False
        results["overall"] = all(v for v in results.values()) if results else True
        return results

