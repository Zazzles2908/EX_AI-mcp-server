from __future__ import annotations

import os
from typing import Any, Dict, List

from .shared.base_tool import BaseTool
from utils.browse_cache import BrowseCache


class BrowseOrchestratorTool(BaseTool):
    name = "browse_orchestrator"
    description = (
        "Plan and optionally fetch a small set of pages for a query, slice relevant sections, and return a citation-annotated summary.\n"
        "Default is dry_run (plan only) to keep CI/offline safe."
    )

    # BaseTool abstract requirements
    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_hops": {"type": "integer", "default": 0},
                "dry_run": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You plan a small browsing workflow and (optionally) fetch pages respecting robots."
        )

    def get_request_model(self):
        from tools.shared.base_models import ToolRequest
        return ToolRequest

    async def prepare_prompt(self, request):  # pragma: no cover - not used
        return ""

    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }

    def run(self, **kwargs) -> Dict[str, Any]:
        query = (kwargs.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        max_hops = int(kwargs.get("max_hops") or 0)
        dry_run = bool(kwargs.get("dry_run") if kwargs.get("dry_run") is not None else True)

        allowed_domains = [d.strip() for d in os.getenv("BROWSE_ALLOWED_DOMAINS", "").split(",") if d.strip()]
        plan: List[Dict[str, Any]] = [
            {"step": 1, "action": "search", "query": query, "note": "Use your preferred search operator heuristics"},
            {"step": 2, "action": "select", "criteria": ["authoritative docs", "recent", "low spam"]},
            {"step": 3, "action": "fetch", "max_hops": max_hops, "respect_robots": True, "allowed_domains": allowed_domains},
            {"step": 4, "action": "slice", "strategy": ["heading-aware", "code-block extraction", "citation capture"]},
            {"step": 5, "action": "summarize", "style": "concise, with citations"},
        ]

        # MVP returns plan only by default; a later iteration can integrate web-fetch
        # and the cache for offline-friendly behavior.
        result: Dict[str, Any] = {
            "query": query,
            "max_hops": max_hops,
            "dry_run": dry_run,
            "allowed_domains": allowed_domains,
            "plan": plan,
        }
        if dry_run:
            return result

        # Non-dry-run path intentionally left minimal to avoid network in CI.
        # It can be extended to call a fetcher and store content in BrowseCache.
        cache = BrowseCache()
        result.update({"fetched": [], "slices": [], "summary": "Non-dry-run not implemented in MVP"})
        return result

