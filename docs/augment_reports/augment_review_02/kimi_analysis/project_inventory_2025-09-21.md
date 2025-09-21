# Phase 1 – Project Inventory (Kimi)

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Top-level purpose
- EX AI MCP Server exposing workflow tools (chat, analyze, planner, thinkdeep, etc.) with provider orchestration (Kimi/GLM) and a WS daemon bridge for IDE MCP clients.

Key folders and roles
- tools/workflows: workflow tools (analyze, thinkdeep, planner, codereview, debug, refactor, precommit, secaudit, testgen, tracer)
- tools/providers/kimi: Kimi-native helpers (chat with tools, uploads, embeddings, cleanup)
- tools/providers/glm: GLM-native helpers (agents API, files, cleanup)
- tools/diagnostics: health, status, ws smoke, toolcall tails, batch markdown review utilities
- tools/orchestrators: autopilot/orchestrate_auto and browse orchestration entrypoints
- src/providers: provider interfaces and registry (kimi, glm, metadata, capabilities, openrouter, openai_compatible, zhipu_optional)
- src/router: high-level routing/service
- src/daemon: websocket session manager and ws_server bridge (aliases + non-empty-first guard applied)

Registration & visibility
- See registry_and_visibility_2025-09-21.md for TOOL_MAP and tiers
- LEAN_MODE/STRICT_LEAN/DISABLED_TOOLS gates confirmed in registry

Environment highlights
- Routing on (balanced), GLM flash default manager, Kimi long-context preference
- WS limits: Kimi/GLM inflight set; progress/keepalive tuned; compatibility text enabled

MCP status (current)
- Chat/analyze tools verified functional through IDE
- Other workflow tools likely need schema/descriptor conformance checks and timeouts alignment

Next: Full Kimi inventory will be inserted here once received; until then, this snapshot ensures we can progress to Phase 3 safely.
