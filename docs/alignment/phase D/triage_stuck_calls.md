# Stuck MCP Call Triage (Phase D)

Use this quick checklist when a tool call appears to hang or take unusually long.

## 1) Identify the request
- Note the tool name and the `req_id` (shown in activity log lines and UI summaries)
- If possible, re-run with a simple prompt to reproduce

## 2) Check logs (all are rotating and safe to tail)
- Main server log: logs/mcp_server.log
- Activity log: logs/mcp_activity.log
- Error-only log: logs/mcp_errors.log

Key lines to look for:
- TOOL_CALL / TOOL_COMPLETED
- [WATCHDOG] warn/error lines with elapsed seconds and req_id
- [PROGRESS] heartbeat lines for long calls
- [ROUTER_DECISION] and [MODEL_ROUTE] for routing context

## 3) JSONL snapshots (optional, if enabled)
- Ensure .env sets EX_TOOLCALL_LOG_PATH (e.g., .logs/toolcalls.jsonl)
- Optionally set EX_MIRROR_ACTIVITY_TO_JSONL=true
- Use tool: toolcall_log_tail (args: {"n": 50}) to view latest sanitized events

## 4) Common causes and actions
- Slow upstream provider or bad network:
  - EX_HTTP_TIMEOUT_SECONDS controls HTTP timeout
  - EX_TOOL_TIMEOUT_SECONDS controls overall tool execution timeout
  - Retry the call; check provider status dashboards if available
- Missing progress/heartbeat:
  - Heartbeats emit every EX_HEARTBEAT_SECONDS (default 10s)
  - Watchdog warns at EX_WATCHDOG_WARN_SECONDS (30s) and errors at EX_WATCHDOG_ERROR_SECONDS (90s)
- Model/router issues:
  - Verify [ROUTER_DECISION] lines; try forcing a simple model (e.g., glm-4.5-flash)

## 5) Quick stabilization knobs (.env)
- EX_HTTP_TIMEOUT_SECONDS=60
- EX_TOOL_TIMEOUT_SECONDS=120
- EX_HEARTBEAT_SECONDS=10
- EX_WATCHDOG_WARN_SECONDS=30
- EX_WATCHDOG_ERROR_SECONDS=90
- EX_MIRROR_ACTIVITY_TO_JSONL=false

Apply changes, restart the EXAI MCP server/shim, and re-run a short smoke:
- status, chat (1-liner), analyze (step 1), codereview (step 1), testgen (small)

## 6) When reporting
Include:
- req_id
- Tool name + arguments summary
- Relevant log snippet (WATCHDOG/PROGRESS/ERROR)
- Provider + model (from MCP Call Summary / routing logs)
- Approx duration before timeout/cancel

