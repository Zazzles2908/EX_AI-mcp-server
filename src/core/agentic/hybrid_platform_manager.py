from __future__ import annotations

import os
from typing import Optional


class HybridPlatformManager:
    """Unified platform management for Moonshot.ai (OpenAI-compatible) and Z.ai.

    Note: This is a scaffolding class; no network calls are made here. It only
    resolves configuration and provides lazy client initializers. Real provider
    clients already exist in providers/ and will be composed here later.
    """

    MOONSHOT_BASE_URL = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")
    ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.zhipuai.cn/api/paas/v4")

    def __init__(self) -> None:
        self._moonshot_initialized = False
        self._zai_initialized = False
        self._moonshot_client = None
        self._zai_client = None

    def get_moonshot_client(self):  # typed: ignore[no-untyped-def]
        """Return OpenAI-compatible client for Moonshot (lazy)."""
        if not self._moonshot_initialized:
            # Defer to providers/openai_compatible.py or providers/kimi.py
            self._moonshot_initialized = True
        return self._moonshot_client

    def get_zai_client(self):  # typed: ignore[no-untyped-def]
        """Return Z.ai client (lazy)."""
        if not self._zai_initialized:
            # Defer to providers/zhipu_optional.py or providers/glm.py
            self._zai_initialized = True
        return self._zai_client

    @classmethod
    def health_defaults(cls) -> dict[str, bool]:
        """Static health defaults used by unit tests without network calls."""
        return {"moonshot": False, "zai": False}

