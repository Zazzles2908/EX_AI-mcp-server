"""
Expert Analysis Configuration (Fallback Shim)

Provides defaults when `config.expert_analysis` package is not available.
This module is intentionally lightweight and driven by environment variables:

- DEFAULT_USE_ASSISTANT_MODEL: 'true'|'false' (default: false)
- EXPERT_ANALYSIS_MODE: 'disabled'|'enabled'|'auto' (default: 'auto')
- EXPERT_ANALYSIS_SHOW_WARNINGS: 'true'|'false' (default: true)
- EXPERT_ANALYSIS_SHOW_COST_SUMMARY: 'true'|'false' (default: true)
- EXPERT_ANALYSIS_MAX_COST_THRESHOLD: float (optional)
- EXPERT_ANALYSIS_TIMEOUT_SECS / EXPERT_HEARTBEAT_INTERVAL_SECS (optional)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    val = (os.getenv(name) or "").strip().lower()
    if val in {"1", "true", "yes", "on"}:
        return True
    if val in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def _env_float(name: str, default: Optional[float] = None) -> Optional[float]:
    try:
        raw = os.getenv(name)
        if raw is None or str(raw).strip() == "":
            return default
        return float(raw)
    except Exception:
        return default


@dataclass
class ExpertAnalysisConfig:
    mode: str = "auto"  # disabled|enabled|auto
    show_warnings: bool = True
    show_cost_summary: bool = True
    max_cost_threshold: Optional[float] = None

    def should_show_warnings(self, tool_name: str) -> bool:  # noqa: ARG002
        return self.show_warnings

    def should_show_cost_summary(self, tool_name: str) -> bool:  # noqa: ARG002
        return self.show_cost_summary


def get_expert_analysis_config() -> ExpertAnalysisConfig:
    mode = (os.getenv("EXPERT_ANALYSIS_MODE") or "auto").strip().lower()
    show_warn = _env_bool("EXPERT_ANALYSIS_SHOW_WARNINGS", True)
    show_cost = _env_bool("EXPERT_ANALYSIS_SHOW_COST_SUMMARY", True)
    max_cost = _env_float("EXPERT_ANALYSIS_MAX_COST_THRESHOLD")
    return ExpertAnalysisConfig(mode=mode, show_warnings=show_warn, show_cost_summary=show_cost, max_cost_threshold=max_cost)


def should_use_expert_analysis(tool_name: str, request_override: Optional[bool] = None) -> bool:  # noqa: ARG001
    """
    Decide whether to use expert analysis.

    Order of precedence:
    1) Explicit request override (use_assistant_model)
    2) Global mode EXPERT_ANALYSIS_MODE: disabled|enabled|auto
    3) DEFAULT_USE_ASSISTANT_MODEL (boolean)
    """
    if request_override is not None:
        return bool(request_override)

    mode = (os.getenv("EXPERT_ANALYSIS_MODE") or "auto").strip().lower()
    if mode == "disabled":
        return False
    if mode == "enabled":
        return True

    # auto mode: fall back to DEFAULT_USE_ASSISTANT_MODEL (default False for safety)
    return _env_bool("DEFAULT_USE_ASSISTANT_MODEL", False)


__all__ = [
    "ExpertAnalysisConfig",
    "get_expert_analysis_config",
    "should_use_expert_analysis",
]

