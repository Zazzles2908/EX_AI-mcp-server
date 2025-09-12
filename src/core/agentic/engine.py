from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .task_router import IntelligentTaskRouter
from .context_manager import AdvancedContextManager


@dataclass
class AgenticDecision:
    platform: str
    estimated_tokens: int
    images_present: bool
    task_type: str


class AutonomousWorkflowEngine:
    """Lightweight engine that provides routing and context hints.

    This scaffolding does not alter tool behavior. It computes metadata that
    callers can attach to responses when feature flags are enabled.
    """

    def __init__(self) -> None:
        self.router = IntelligentTaskRouter()
        self.ctx = AdvancedContextManager()

    def decide(self, request_like: Dict[str, Any]) -> AgenticDecision:
        platform = self.router.select_platform(request_like)
        # Estimate tokens from messages
        messages = request_like.get("messages", [])
        estimated = self.ctx.estimate_tokens(messages)
        images_present = any("images" in m for m in messages if isinstance(m, dict))
        task_type = self.router.classify(request_like).value
        return AgenticDecision(
            platform=platform,
            estimated_tokens=estimated,
            images_present=images_present,
            task_type=task_type,
        )

