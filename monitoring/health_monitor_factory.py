from __future__ import annotations

import asyncio
from typing import Dict

from monitoring.health_monitor import HealthMonitor
from src.providers.hybrid_platform_manager import HybridPlatformManager


def build_health_monitor_with_platforms(hpm: HybridPlatformManager) -> HealthMonitor:
    hm = HealthMonitor()

    async def ping(platform: str) -> bool:
        return await hpm.simple_ping(platform)

    def ping_sync(platform: str) -> bool:
        # Prefer asyncio.run when no loop is running; otherwise use a fresh loop
        try:
            asyncio.get_running_loop()
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(ping(platform))
            finally:
                loop.close()
        except RuntimeError:
            # No running loop
            return asyncio.run(ping(platform))

    hm.add_probe("moonshot", lambda: ping_sync("moonshot"))
    hm.add_probe("zai", lambda: ping_sync("zai"))
    return hm

