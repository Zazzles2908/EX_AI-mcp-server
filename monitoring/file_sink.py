from __future__ import annotations

import json
import os
from typing import Dict, Any

from monitoring.telemetry import MetricsSink


class FileMetricsSink(MetricsSink):
    """MetricsSink that can flush counters/timers to a JSONL file with size rotation."""

    def __init__(self, path: str = "logs/metrics.jsonl", max_bytes: int = 1_000_000) -> None:
        super().__init__()
        self.path = path
        self.max_bytes = max_bytes
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _rotate_if_needed(self) -> None:
        try:
            if os.path.exists(self.path) and os.path.getsize(self.path) > self.max_bytes:
                base, ext = os.path.splitext(self.path)
                rotated = f"{base}.1{ext or ''}"
                if os.path.exists(rotated):
                    os.remove(rotated)
                os.replace(self.path, rotated)
        except Exception:
            # Best-effort rotation only
            pass

    def flush(self) -> None:
        self._rotate_if_needed()
        out: Dict[str, Any] = {
            "counters": {k: v.value for k, v in self.counters.items()},
            "timers": {k: t.durations for k, t in self.timers.items()},
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(out) + "\n")

