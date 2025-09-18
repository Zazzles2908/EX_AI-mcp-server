from monitoring.predictive import HealthTrendStore


def test_health_trend_store_degrading():
    ht = HealthTrendStore(window=3, threshold=0.9)
    ht.add_metric(1.0)
    ht.add_metric(0.8)
    assert ht.is_degrading() is False
    ht.add_metric(0.7)
    assert ht.is_degrading() is True

