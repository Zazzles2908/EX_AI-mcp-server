from monitoring.autoscale import should_scale_up, should_scale_down


def test_autoscale_simple_rules():
    up = should_scale_up([10, 5], avg_latency_ms=1600, max_workers=10, current_workers=2)
    down = should_scale_down([0, 0], avg_latency_ms=200, min_workers=1, current_workers=3)
    assert up is True and down is True

