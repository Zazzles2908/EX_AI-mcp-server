from __future__ import annotations

from contextlib import contextmanager
from typing import Optional

from monitoring.telemetry import MetricsSink


@contextmanager
def instrument(sink: MetricsSink, op_name: str, success_counter: Optional[str] = None):
    t = sink.timer(f"latency.{op_name}")
    done = t.timeit()
    try:
        yield
        if success_counter:
            sink.counter(success_counter).inc(1)
    finally:
        done()

