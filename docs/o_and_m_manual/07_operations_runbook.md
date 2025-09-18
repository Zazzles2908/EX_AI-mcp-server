# Operations Runbook

## First 15 minutes (fresh install)
1) Start server: `python -m server`
2) From client: call `status`, `version`, `listmodels`
3) Run smoke: `python tools/ws_daemon_smoke.py`
4) Tail logs: `Get-Content -Path logs\mcp_activity.log -Tail 200 -Wait`

Acceptance (quick):
- stream_demo: fallback (zai) OK; streaming (moonshot) returns first chunk
- thinkdeep (web cue): completes; routes per rules
- chat_longcontext: executes; route depends on context/hints

## Daily operations
- Watch mcp_activity.log for MCP_CALL_SUMMARY (model, tokens, duration)
- Re-run smoke when changing env keys or routing preferences
- Periodically run quality checks (see Testing & Validation)

## Health checks (manual)
- status/version: complete with success
- listmodels: shows providers/models expected for your keys
- provider_capabilities: context_window and feature flags visible

## Triage playbook
1) Error in activity log → open the preceding TOOL_CALL; verify args
2) Wrong model route → confirm estimated_tokens/long_context hints present
3) Streaming issue → stream_demo should use async path (already implemented)
4) No tools listed → check LEAN_MODE/LEAN_TOOLS allowlist and DISABLED_TOOLS

## Safe validation runs
- Unit tests: `python -m pytest tests/ -v -m "not integration"`
- Quick simulator: `python communication_simulator_test.py --quick`
- Full smoke: `python tools/ws_daemon_smoke.py`

