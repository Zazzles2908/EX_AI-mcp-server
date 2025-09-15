"""
Cost-aware Model Router for EX AI MCP tools.

Decides an initial model given tool context and lightweight heuristics.
Goals:
- Default to fast, low-cost GLM flash for most tasks
- Escalate to higher-quality GLM selectively
- Prefer Kimi for long-context text/vision or when explicitly requested

Environment knobs:
- EX_ROUTING_PROFILE: speed|balanced|quality (default: balanced)
- ROUTER_ENABLED: true|false (default: false)

This is intentionally lightweight; future versions can incorporate
uncertainty signals and feedback loops.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class RoutingContext:
    tool_name: str
    prompt: str | None = None
    files_count: int = 0
    images_count: int = 0
    requested_model: Optional[str] = None


class ModelRouter:
    @staticmethod
    def _profile() -> str:
        return (os.getenv("EX_ROUTING_PROFILE") or "balanced").strip().lower()

    @staticmethod
    def is_enabled() -> bool:
        return (os.getenv("ROUTER_ENABLED", "false").strip().lower() == "true")

    @staticmethod
    def decide(ctx: RoutingContext) -> str:
        """Return model name based on tool and simple heuristics.

        Rules of thumb:
        - If user provided a non-auto model, honor it
        - Secaudit: prefer quality tier by default
        - Images present or vision keywords: prefer Kimi family
        - For refactor/codereview/debug/analyze/testgen: flash first
        - Profile=quality upgrades some tools to glm-4.5
        """
        # Honor explicit model when not auto
        if ctx.requested_model and str(ctx.requested_model).strip().lower() not in {"", "auto"}:
            return ctx.requested_model

        profile = ModelRouter._profile()
        tool = (ctx.tool_name or "").lower()
        prompt_l = (ctx.prompt or "").lower()

        # Vision / images → Kimi family
        if ctx.images_count > 0 or any(k in prompt_l for k in ("vision", "image", "diagram")):
            return os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")

        # Security audits → quality by default
        if tool == "secaudit" or any(k in prompt_l for k in ("security", "auth", "secrets", "compliance")):
            return os.getenv("GLM_QUALITY_MODEL", "glm-4.5")

        # Core code tools default: flash tier
        if tool in {"codereview", "refactor", "debug", "analyze", "testgen", "tracer", "planner", "precommit"}:
            model = os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
            # Profile-driven bump
            if profile == "quality" and tool in {"codereview", "refactor", "secaudit", "debug"}:
                model = os.getenv("GLM_QUALITY_MODEL", "glm-4.5")
            return model

        # Chat and everything else: flash first
        if profile == "quality":
            return os.getenv("GLM_QUALITY_MODEL", "glm-4.5")
        return os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")


def select_kimi_model(ctx: RoutingContext, expected_output_tokens: int | None = None) -> str:
    """Heuristic Kimi model selector inspired by Moonshot docs.

    Env overrides:
    - KIMI_SIMPLE_MODEL (default: kimi-k2-turbo-preview)
    - KIMI_CODE_MODEL (default: kimi-k2-0905-preview)
    - KIMI_GENERAL_MODEL (default: kimi-k2-0711-preview)
    - KIMI_CREATIVE_MODEL (default: kimi-latest)
    - KIMI_LONG_CONTEXT_MODEL (default: kimi-latest)
    """
    import os as _os

    simple = _os.getenv("KIMI_SIMPLE_MODEL", "kimi-k2-0711-preview")
    code = _os.getenv("KIMI_CODE_MODEL", "kimi-k2-0905-preview")
    general = _os.getenv("KIMI_GENERAL_MODEL", "kimi-k2-0711-preview")
    creative = _os.getenv("KIMI_CREATIVE_MODEL", "kimi-latest")
    longctx = _os.getenv("KIMI_LONG_CONTEXT_MODEL", "kimi-latest")

    prompt = (ctx.prompt or "")
    pl = len(prompt)
    tool = (ctx.tool_name or "").lower()
    p_lower = prompt.lower()

    # Estimate tokens cheaply
    est_in_tokens = max(1, pl // 4)
    est_out_tokens = expected_output_tokens or (
        1500 if tool in {"codereview", "analyze", "refactor", "debug"} else 400
    )

    # Content-based signals
    code_keywords = ("code", "function", "class", "def ", "bug", "stack trace", "traceback", "refactor")
    creative_keywords = ("story", "poem", "creative", "imagine")

    if any(k in p_lower for k in code_keywords) or tool in {"codereview", "refactor", "debug", "testgen"}:
        # Code tasks → optimized k2 code model
        return code

    if any(k in p_lower for k in creative_keywords):
        return creative

    # Simple Q&A heuristic
    if pl < 100 and est_out_tokens < 1000 and ctx.files_count == 0:
        return simple

    # Long context or many files → long-context friendly model
    if pl > 1000 or est_out_tokens > 2000 or ctx.files_count > 10:
        return longctx

    # Default general-purpose
    return general





def get_fallback_choice(primary_provider, tool_name: str):
    """Return (ProviderType, model_name) for fallback under rate-limit/latency in a cost-aware way.

    Strategy (configurable via env):
    - When primary is GLM: prefer cheaper Kimi k2 family before expensive thinking models
      * KIMI_FALLBACK_ORDER (comma list) default: kimi-k2-0711-preview,kimi-k2-0905-preview,kimi-latest
      * To allow expensive thinking fallback, set KIMI_ALLOW_EXPENSIVE_THINKING_FALLBACK=true (appends kimi-thinking-preview)
    - When primary is Kimi: prefer cheaper GLM variants first
      * GLM_FALLBACK_ORDER (comma list) default: glm-4.5-air,glm-4.5-flash,glm-4.5
    Returns (None, None) if ProviderType is unavailable.
    """
    try:
        # Import lazily to avoid import cycles during startup
        from src.providers.base import ProviderType
    except Exception:
        return None, None

    def _parse_list(name: str, default: list[str]) -> list[str]:
        raw = os.getenv(name)
        if not raw:
            return list(default)
        return [s.strip() for s in raw.split(",") if s.strip()]

    pv = getattr(primary_provider, "value", str(primary_provider)).lower()
    if pv == "glm":
        order = _parse_list(
            "KIMI_FALLBACK_ORDER",
            [
                "kimi-k2-0711-preview",
                "kimi-k2-0905-preview",
                "kimi-latest",
            ],
        )
        if os.getenv("KIMI_ALLOW_EXPENSIVE_THINKING_FALLBACK", "false").strip().lower() == "true":
            order.append("kimi-thinking-preview")
        # Tool-based tweak: bias toward 0905 for code tools (cheaper than thinking, good for code)
        if tool_name.lower() in {"codereview", "refactor", "debug", "analyze", "testgen"}:
            if "kimi-k2-0905-preview" in order:
                order.remove("kimi-k2-0905-preview")
                order.insert(0, "kimi-k2-0905-preview")
        return ProviderType.KIMI, (order[0] if order else os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))

    if pv == "kimi":
        order = _parse_list(
            "GLM_FALLBACK_ORDER",
            [
                "glm-4.5-air",
                "glm-4.5-flash",
                "glm-4.5",
            ],
        )
        # Bias toward flash for code tools
        if tool_name.lower() in {"codereview", "refactor", "debug", "analyze", "testgen"}:
            if "glm-4.5-flash" in order:
                order.remove("glm-4.5-flash")
                order.insert(0, "glm-4.5-flash")
        return ProviderType.GLM, (order[0] if order else os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash"))

    return None, None

__all__ = ["ModelRouter", "RoutingContext", "get_fallback_choice"]

