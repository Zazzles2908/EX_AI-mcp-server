"""
AI Manager (P4 scaffolding)
- Env-gated, non-operational by default
- No routing changes yet; provides a place for decision logic later
"""
from __future__ import annotations
import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AiManager:
    """Scaffold for an AI Manager responsible for high-level routing/planning.

    Notes:
    - Enabled via EX_AI_MANAGER_ENABLED. Defaults to False.
    - Strategy is advisory only for now (no-op).
    - plan_or_route() currently logs and returns None (no behavior change).
    """

    def __init__(self, enabled: bool | None = None) -> None:
        if enabled is None:
            enabled = os.getenv("EX_AI_MANAGER_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.enabled: bool = bool(enabled)
        self.strategy: str = os.getenv("EX_AI_MANAGER_STRATEGY", "manager-first").strip() or "manager-first"
        self.log_level: str = os.getenv("EX_AI_MANAGER_LOG_LEVEL", "INFO").strip().upper() or "INFO"

        # Set module logger level (does not affect root)
        try:
            logger.setLevel(getattr(logging, self.log_level, logging.INFO))
        except Exception:
            logger.setLevel(logging.INFO)

        if self.enabled:
            logger.info("AI Manager scaffold enabled (strategy=%s) — no routing changes yet", self.strategy)
        else:
            logger.debug("AI Manager scaffold disabled")

    def plan_or_route(self, tool_name: str, arguments: Optional[dict[str, Any]] = None):
        """Advisory-only DRY-RUN plan.

        Returns a small advisory dict when both flags are enabled:
        - EX_AI_MANAGER_ENABLED=true and EX_AI_MANAGER_ADVISORY=true
        Otherwise returns None. No routing changes are performed here.
        """
        try:
            if not self.enabled:
                return None
            advisory = os.getenv("EX_AI_MANAGER_ADVISORY", "false").strip().lower() in {"1","true","yes","on"}
            model_hint = (arguments or {}).get("model", "auto")
            has_files = False
            for key in ("files", "file_ids", "images", "attachments"):
                if isinstance(arguments, dict) and key in arguments and arguments.get(key):
                    has_files = True
                    break
            suggested = "kimi" if has_files else "glm"
            if advisory:
                plan = {
                    "advisory": True,
                    "strategy": self.strategy,
                    "tool": tool_name,
                    "model_hint": model_hint,
                    "has_files": has_files,
                    "suggested_provider": suggested,
                    "suggested_model": "kimi-k2-0905-preview" if has_files else "glm-4.5-flash",
                    "websearch": bool(arguments and arguments.get("use_websearch", False)),
                }
                logger.debug("[AI-MANAGER-PLAN] %s", plan)
                return plan
            else:
                logger.debug("[AI-MANAGER-DRYRUN] tool=%s model_hint=%s strategy=%s", tool_name, model_hint, self.strategy)
                return None
        except Exception as e:  # pragma: no cover
            logger.debug("[AI-MANAGER-DRYRUN] skip: %s", e)
            return None

