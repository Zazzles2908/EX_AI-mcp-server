# Effective Information Flow and Layering Blueprint (EXAI MCP)

## Purpose
A concise, practical layering that makes the system predictable for day‑to‑day use while keeping room for the hybrid agentic roadmap. This is written for solution designers first (plain language).

## Layers (top to bottom)
- Client UI (VS Code + Augment extension)
  - Sends MCP tool calls; shows streamed progress and final blocks
- WS Shim / Daemon
  - Stable WebSocket bridge for the client to talk to our server
- MCP Server Boundary (server.py)
  - Validates requests, resolves model, enforces file/size rules, attaches progress
- Router + ModelProviderRegistry
  - Picks the model/provider (GLM, Kimi) with fallbacks
- Tools Layer (chat, analyze, codereview, planner, thinkdeep, etc.)
  - Business behavior; use SimpleTool/WorkflowTool base classes
- Providers (GLM, Kimi, Moonshot later)
  - Model-specific API calls
- Storage & Logs (logs/*.log)
  - Server and tool activity with rotation
- Docs (docs/alignment, docs/sweep_reports/current_exai_reviews)
  - Human-friendly run logs + reports

## End-to-end flow (what happens)
1) You ask the tool (e.g., chat/analyze) with prompt + optional files
2) WS shim forwards to MCP server (stdio/WS)
3) Server boundary:
   - Resolves model (or falls back)
   - Validates file sizes and basic shape
   - Sets defaults (e.g., use_websearch if enabled)
4) Tool executes with the resolved model
5) Server attaches progress logs to the final TextContent (JSON) and an optional top summary
6) UI shows streamed “[PROGRESS] …” lines, then the final answer

## Data lifecycle & safeguards
- Files: attach absolute paths; server checks readability and size per model budget
- Token/cost: choose glm-4.5-flash for low-cost passes; bump thinking_mode or model as needed
- Environment toggles (safe by default; enable sparingly):
  - INJECT_CURRENT_DATE=true (adds today’s date)
  - ENABLE_SMART_WEBSEARCH=false|true (auto web for time-sensitive prompts)
  - EX_AUTOCONTINUE_WORKFLOWS=false (guard against runaway steps)
- Security posture: keep .env ignored; no secrets in PRs; use pre-push safety check

## Observability
- Logs: logs/mcp_server.log (all activity), logs/mcp_activity.log (tool calls)
- Quick reads:
  - tail -n 100 logs/mcp_server.log
  - tail -n 100 logs/mcp_activity.log
- Optional UI summary line:
  - Set EX_ACTIVITY_SUMMARY_AT_TOP=true to inject a compact “Activity: … events (req_id=…)” at the top of the response
- Run logs in docs: summarize each call in “compact MCP Call Summary” format under docs/alignment/mcp_runs

## Guardrails & staged flips
- Keep “Option B” provider shim staged/inactive until consolidation is proven
- Guarded flip plan:
  - Flip a single import site → src.providers.registry
  - CI rule: forbid legacy providers.* imports
  - Telemetry: include provider/model on every call
  - Fast revert path

## Minimal UX toggles (recommended defaults)
- LOG_LEVEL=INFO (clear progress, not too noisy)
- EX_ACTIVITY_SUMMARY_AT_TOP=true (helps UI readability)
- CLIENT_DEFAULT_THINKING_MODE=medium (balanced)
- CLIENT_DEFAULTS_USE_WEBSEARCH=false (opt-in web to control cost)

## EXAI MCP routes to use (practical quick-start)
- Health/Status snapshot
  - status_exai-mcp with hub=true, include_tools=true
- Quick QA (project-specific)
  - chat_exai-mcp on glm-4.5-flash with small, targeted file set
- Deeper review (structured)
  - analyze_exai-mcp for 1–2 step short reports
  - codereview_exai-mcp when you want a multi-step, evidence‑backed code review
- Test generation
  - testgen_exai-mcp to propose focused tests for a module/function
- Planning
  - planner_exai-mcp to break down multi‑step work with next‑step gating

## Small system map (Mermaid)
```mermaid
flowchart TD
  A[User in VS Code] --> B[WS Shim/Daemon]
  B --> C[MCP Server Boundary]
  C --> D[Router + ModelProviderRegistry]
  D --> E[Tool (chat/analyze/thinkdeep...)]
  E --> F[Provider (GLM/Kimi)]
  F --> E
  E --> C
  C --> G[Progress + Final TextContent]
  G --> H[UI (progress + final blocks)]
```

## What to remember
- Keep EXAI MCP as the main path: status → quick QA → deeper review → tests, all within token budgets
- Prefer src.* imports and documented shims; flip Option B ONLY with guards
- Always return a compact top summary for human‑friendly UI, then the details

