# Phase 1 – Import & Dependency Mapping (Kimi)

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Core graphs
- server.py -> tools.* (ChatTool, AnalyzeTool, PlannerTool, ThinkDeepTool, etc.)
- tools/registry.py -> imports tool classes lazily via __import__; visibility/gating via env
- tools/providers/* -> provider SDK wrappers (Kimi, GLM); used by workflow tools or orchestrators
- src/providers/* -> capability definitions and routing helpers used by server/router
- src/router/service.py -> manager-first routing entry (to be expanded in Phase 3)
- src/daemon/ws_server.py -> IDE bridge for WS; normalizes tool aliases; enforces non-empty-first output

Critical execution paths
- IDE -> WS daemon -> server tool dispatch -> provider calls -> WS response -> IDE payload
- Registry gating (LEAN/DISABLED) influences exposure and discovery

Risk areas
- Mismatch between TOOL_MAP and actual module/class names after refactors
- Timeouts/retries not consistently honored across all workflow tools
- Missing get_descriptor() in some tools can break list_tools UX

Immediate actions
1) Confirm server TOOLS map aligns with registry ToolRegistry
2) Standardize timeouts (TOOL_EXEC_TIMEOUT_SEC + per-tool) and retries (RESILIENT_*)
3) Ensure provider modules exit early on misconfig (clear error)

Will be enhanced with the Kimi-generated dependency map on arrival.
