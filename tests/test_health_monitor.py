from monitoring.health_monitor import HealthMonitor


def test_health_monitor_status():
    hm = HealthMonitor()
    hm.add_probe("ok1", lambda: True)
    hm.add_probe("ok2", lambda: True)
    st = hm.status()
    assert st["ok1"] and st["ok2"] and st["overall"] is True

