"""
RouterService: central model routing and availability preflight for EX MCP Server.

- Preflight on startup checks provider/model availability and performs trivial
  chat probes (env-gated) to validate connectivity.
- Decision logging outputs JSON lines via the 'router' logger.
- Simple choose_model() policy that honors explicit model requests and falls back
  to preferred fast model (GLM) or long-context model (Kimi) when 'auto'.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from typing import Optional, Dict, Any

from src.providers.registry import ModelProviderRegistry as R
from src.providers.base import ProviderType

logger = logging.getLogger("router")


@dataclass
class RouteDecision:
    requested: str
    chosen: str
    reason: str
    provider: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        return json.dumps({
            "event": "route_decision",
            "requested": self.requested,
            "chosen": self.chosen,
            "reason": self.reason,
            "provider": self.provider,
            "meta": self.meta or {},
        }, ensure_ascii=False)


class RouterService:
    def __init__(self) -> None:
        # Env-tunable preferred models
        self._fast_default = os.getenv("FAST_MODEL_DEFAULT", "glm-4.5-flash")
        self._long_default = os.getenv("LONG_MODEL_DEFAULT", "kimi-k2-0711-preview")
        # Minimal JSON logging
        logger.setLevel(getattr(logging, os.getenv("ROUTER_LOG_LEVEL", "INFO").upper(), logging.INFO))

    def preflight(self) -> None:
        """Check provider readiness and log available models; optionally probe chat."""
        try:
            avail = R.get_available_models(respect_restrictions=True)
            by_provider: Dict[str, list[str]] = {}
            for name, ptype in avail.items():
                by_provider.setdefault(ptype.name, []).append(name)
            logger.info(json.dumps({
                "event": "preflight_models",
                "providers": {k: sorted(v) for k, v in by_provider.items()},
            }, ensure_ascii=False))
        except Exception as e:
            logger.warning(json.dumps({"event": "preflight_models_error", "error": str(e)}))

        # Optional trivial chat probe (env: ROUTER_PREFLIGHT_CHAT=true)
        if (os.getenv("ROUTER_PREFLIGHT_CHAT", "true").strip().lower() == "true"):
            self._probe_chat_safely()

    def _probe_chat_safely(self) -> None:
        prompt = "ping"
        for candidate in [self._fast_default, self._long_default]:
            prov = R.get_provider_for_model(candidate)
            if not prov:
                continue
            try:
                # Short, cheap call with small max_output_tokens when supported
                resp = prov.generate_content(prompt=prompt, model_name=candidate, max_output_tokens=8, temperature=0)
                logger.info(json.dumps({
                    "event": "preflight_chat_ok",
                    "model": candidate,
                    "provider": prov.get_provider_type().name,
                    "usage": getattr(resp, "usage", None) or {},
                }, ensure_ascii=False))
            except Exception as e:
                logger.warning(json.dumps({
                    "event": "preflight_chat_fail",
                    "model": candidate,
                    "provider": getattr(prov, "get_provider_type", lambda: type("X", (), {"name":"unknown"}))().name,
                    "error": str(e),
                }, ensure_ascii=False))

    def choose_model(self, requested: Optional[str]) -> RouteDecision:
        """Resolve a model name. If 'auto' or empty, choose a sensible default based on availability."""
        req = (requested or "auto").strip()
        if req.lower() != "auto":
            # Honor explicit request if available
            prov = R.get_provider_for_model(req)
            if prov is not None:
                dec = RouteDecision(requested=req, chosen=req, reason="explicit", provider=prov.get_provider_type().name)
                logger.info(dec.to_json())
                return dec
            # Fallback if explicit is unknown
            logger.info(json.dumps({"event": "route_explicit_unavailable", "requested": req}))
        # Auto selection policy: prefer fast GLM, else Kimi long-context, else any available
        for candidate in [self._fast_default, self._long_default]:
            prov = R.get_provider_for_model(candidate)
            if prov is not None:
                dec = RouteDecision(requested=req, chosen=candidate, reason="auto_preferred", provider=prov.get_provider_type().name)
                logger.info(dec.to_json())
                return dec
        # Last resort: pick first available model
        try:
            avail = R.get_available_models(respect_restrictions=True)
            if avail:
                first = sorted(avail.keys())[0]
                prov = R.get_provider_for_model(first)
                dec = RouteDecision(requested=req, chosen=first, reason="auto_first_available", provider=(prov.get_provider_type().name if prov else None))
                logger.info(dec.to_json())
                return dec
        except Exception:
            pass
        # No models available
        dec = RouteDecision(requested=req, chosen=req, reason="no_models_available", provider=None)
        logger.warning(dec.to_json())
        return dec

