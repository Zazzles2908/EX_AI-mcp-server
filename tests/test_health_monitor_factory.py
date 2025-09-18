from monitoring.health_monitor_factory import build_health_monitor_with_platforms

class DummyHPM:
    async def simple_ping(self, platform: str) -> bool:
        return True

def test_health_monitor_factory_status():
    hm = build_health_monitor_with_platforms(DummyHPM())
    st = hm.status()
    assert st["overall"] is True

