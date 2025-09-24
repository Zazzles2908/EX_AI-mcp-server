"""Telemetry scaffolding for EX MCP Server.

Purpose: centralize lightweight observability hooks used by the server, tools,
and orchestrators. This initial module provides no-op helpers to avoid churn.
"""
from __future__ import annotations
from typing import Any

class Telemetry:
    def record_event(self, name: str, **fields: Any) -> None:
        # No-op first pass. Server will keep using existing logging.
        pass

telemetry = Telemetry()

