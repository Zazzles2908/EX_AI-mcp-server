from monitoring.slo import SLO


def test_slo_evaluation():
    slo = SLO(latency_p95_ms=1000, success_rate=0.99)
    assert slo.evaluate({"p95_ms": 900, "success_rate": 0.995}) is True
    assert slo.evaluate({"p95_ms": 1200, "success_rate": 0.995}) is False

