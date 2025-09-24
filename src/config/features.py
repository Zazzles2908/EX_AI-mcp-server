"""Feature flag and env helpers for EX-AI MCP Server.

Centralize boolean flags and small config getters to reduce os.getenv
usage scattered across server.py and tools.
"""
from __future__ import annotations

import os
from typing import Set


TRUE_SET = {"1", "true", "yes", "on"}


def _norm(v: str | None, default: str = "false") -> str:
    if v is None or v == "":
        v = default
    return str(v).strip().lower()


def env_true(key: str, default: str = "false") -> bool:
    """Return True if the env var represents a truthy value."""
    return _norm(os.getenv(key), default) in TRUE_SET


def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def tools_core_only() -> bool:
    return env_true("TOOLS_CORE_ONLY", "false")


def tools_allowlist() -> Set[str]:
    raw = get_env("TOOLS_ALLOWLIST", "")
    return {t.strip().lower() for t in raw.split(",") if t.strip()}


def enable_smart_chat() -> bool:
    return env_true("ENABLE_SMART_CHAT", "false")


def enable_zhipu_native() -> bool:
    return env_true("ENABLE_ZHIPU_NATIVE", "false")


def enable_moonshot_native() -> bool:
    return env_true("ENABLE_MOONSHOT_NATIVE", "false")

