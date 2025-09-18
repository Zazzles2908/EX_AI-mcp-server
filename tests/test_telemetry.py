from monitoring.telemetry import MetricsSink
import time

def test_metrics_sink_counters_and_timers():
    m = MetricsSink()
    c = m.counter("requests")
    c.inc()
    assert c.value == 1
    t = m.timer("latency")
    done = t.timeit()
    time.sleep(0.005)
    done()
    assert t.avg() > 0

