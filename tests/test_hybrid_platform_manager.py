import asyncio
from providers.hybrid_platform_manager import HybridPlatformManager


def test_hybrid_platform_manager_health_keys_present():
    m = HybridPlatformManager()
    res = asyncio.get_event_loop().run_until_complete(m.health_check())
    assert set(res.keys()) == {"moonshot", "zai"}
    assert isinstance(res["moonshot"], bool)
    assert isinstance(res["zai"], bool)

