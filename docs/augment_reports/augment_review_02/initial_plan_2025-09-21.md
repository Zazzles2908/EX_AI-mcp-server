## YES/NO Summary
YES — Proceed with registry-first stabilization of MCP tools today (non-destructive), add server-level ui_summary wrapper, and defer file moves until smokes are green.

## Current state (from docs)
- Tools reorg plan approved; registry remains single source of truth.
- Only chat and analyze workflows are consistently functional; others fail (arg schema, registry gaps, path issues).
- Universal UI wrapper planned at server layer; ThinkDeep currently only tool emitting ui_summary.
- Duplications: streaming demos, provider cleanup scripts; orphans like selfcheck/embed_router.

## Prioritized approach (today)
1) Server-level ui_summary wrapper (feature-flagged) — add consistent UI metadata to all ToolOutput without touching tools.
2) Registry + argument validation pass — enforce schema/required fields per tool; add clear error messages.
3) Minimal fixes for broken tools — align param shapes, normalize file path handling, ensure continuation_id propagation where applicable.
4) Smoke validations — run list_tools, chat, analyze, thinkdeep; provider ops (Kimi/GLM) basic paths; router diagnostics.
5) Defer file moves/dedup until smokes pass — then perform consolidated PR of reorg and shims/cleanup.

## 30/60/90 minute plan
- 0–30 min: 
  - Implement server ui_summary wrapper (flag: UI_WRAPPER=on). 
  - Add schema guards to 2–3 most-used tools (thinkdeep, tracer, codereview) modeled after chat/analyze.
  - Prepare router/diagnostics smoke checklist.
- 30–60 min: 
  - Fix parameter mismatches in tracer/debug/precommit entrypoints.
  - Validate GLM manager-first routing with unpredictable prompts; confirm tool delegation works.
  - Run provider ops smokes (Kimi upload + GLM browse) without side effects.
- 60–90 min: 
  - Consolidate verification results; open follow-up tasks for remaining broken tools.
  - Draft reorg batch move plan; confirm registry shims strategy.
  - Write summary and next-step PR notes.

## Assumptions & risks
- Assumes environment keys loaded; EXAI-WS daemon stable post-restart.
- Risk: hidden import cycles after ui wrapper injection; mitigate with feature flag + quick rollback.
- Risk: inconsistent tool argument schemas; mitigate with centralized validators and better error messages.

## Validation checklist
- Router checks: manager classifies simple vs complex; Planner delegates correctly.
- Diagnostics: list_tools count stable; hidden tools remain hidden unless enabled.
- Unpredictable prompt smokes: chat/analyze/thinkdeep return real, non-hardcoded outputs.
- Provider-safe diagnostics: Kimi file ops + GLM browsing succeed; no stateful writes.
- Universal UI: ui_summary present on all tools; raw outputs preserved unchanged.

## Immediate next steps
- Land ui_summary wrapper and schema guards (small PR).
- Inventory broken tools by error type and prioritize quick wins.
- Prepare reorg batch plan + shims; delay deletes until post-smoke.

