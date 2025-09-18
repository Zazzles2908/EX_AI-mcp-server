from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class TaskType(Enum):
    VISUAL_ANALYSIS = "visual_analysis"
    LONG_CONTEXT_ANALYSIS = "long_context_analysis"
    CODE_GENERATION = "code_generation"
    MULTIMODAL_REASONING = "multimodal_reasoning"
    COMPLEX_WORKFLOWS = "complex_workflows"


class IntelligentTaskRouter:
    """Agentic capability/context-length based router (Phase E/F/G).

    Goals:
    - Keep GLM (zai) as the fast "manager" for simple/normal prompts
    - Escalate to Moonshot/Kimi for long-context or large multimodal needs
    - Prefer Z.ai when web browsing is needed (strong built-in web search)

    Rules (ordered):
    1) Multimodal/images present -> 'zai' (GLM)  [can be adjusted to moonshot vision if preferred]
    2) Web needed (explicit use_websearch or URL/time-sensitive cues) -> 'zai'
    3) Estimated tokens > 128k -> 'moonshot' (max context)
       Estimated tokens > 48k  -> 'moonshot' (long context)
    4) task_type mapping, else default -> 'zai' (GLM manager)
    """

    def __init__(self) -> None:
        # Bias towards GLM for general/manager tasks; Moonshot for long-context
        self.routing_rules = {
            TaskType.VISUAL_ANALYSIS: "zai",
            TaskType.LONG_CONTEXT_ANALYSIS: "moonshot",
            TaskType.CODE_GENERATION: "zai",
            TaskType.MULTIMODAL_REASONING: "zai",
            TaskType.COMPLEX_WORKFLOWS: "zai",
        }

    def _estimate_context_tokens(self, request: Dict[str, Any]) -> int:
        """Estimate tokens from available fields.
        Prefer explicit 'estimated_tokens' when provided; else fall back to messages/prompt.
        Heuristic: ~4 chars per token.
        """
        try:
            et = request.get("estimated_tokens")
            if et is not None:
                et_int = int(et)
                if et_int > 0:
                    return et_int
        except Exception:
            pass
        msgs = request.get("messages") or []
        parts = [str(m) for m in msgs]
        # Fall back to common single-text fields when messages are not provided
        for key in ("prompt", "text", "content"):
            val = request.get(key)
            if isinstance(val, str) and val:
                parts.append(val)
        text = " ".join(parts)
        return max(0, len(text) // 4)

    def _has_multimodal(self, request: Dict[str, Any]) -> bool:
        return bool(request.get("images") or request.get("has_images"))

    def _contains_url_or_timesensitive(self, request: Dict[str, Any]) -> bool:
        msgs = request.get("messages") or []
        hay = " ".join([str(m).lower() for m in msgs])
        url_like = ("http://" in hay) or ("https://" in hay) or ("www." in hay) or (".com" in hay)
        time_cues = any(k in hay for k in ("today", "latest", "current", "news", "as of", "2025"))
        return url_like or time_cues

    def _needs_web(self, request: Dict[str, Any]) -> bool:
        if bool(request.get("use_websearch")):
            return True
        return self._contains_url_or_timesensitive(request)

    def select_platform(self, request: Dict[str, Any]) -> str:
        # 1) Multimodal first
        if self._has_multimodal(request):
            return "zai"
        # 2) Web needs -> GLM (strong built-in browse/search)
        if self._needs_web(request):
            return "zai"
        # 3) Context thresholds
        tokens = self._estimate_context_tokens(request)
        if tokens > 128_000:
            return "moonshot"
        if tokens > 48_000:
            return "moonshot"
        # 4) Task-type mapping, default to GLM manager
        try:
            t = TaskType(request.get("task_type"))
            return self.routing_rules.get(t, "zai")
        except Exception:
            return "zai"

