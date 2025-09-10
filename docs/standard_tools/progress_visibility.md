# Real-time Tool Progress Visibility (EX MCP Server)

This document explains how EX MCP Server emits real-time progress breadcrumbs during tool execution and how you can see them in VS Code (Augment Code) and Auggie CLI.

## What changed

- Added a centralized progress helper `utils/progress.py` with:
  - `send_progress(message: str, level: str = "info")` for emitting progress
  - `set_mcp_notifier(...)` hook for future MCP-native notifications
- Default streaming mode controlled by `STREAM_PROGRESS` (default: true)
- Wrapper now defaults `LOG_LEVEL=INFO` when `AUGGIE_CLI=true` or `STREAM_PROGRESS=true`
- Workflow tools (analyze, thinkdeep, codereview, debug, precommit, refactor, secaudit, planner, consensus, testgen, tracer) emit progress at key milestones via BaseWorkflowMixin
- Simple tools (like chat) also emit minimal progress via SimpleTool

## How it works

- Tools call `send_progress("message")` at key milestones
- Messages go to the `mcp_activity` logger at INFO level as `[PROGRESS] ...`
- MCP notifier hook (best-effort) is registered on server startup to allow future MCP-native notifications

## How to see progress

### VS Code (Augment Code)
- Open the Output panel or the extension’s tool activity channel while a tool runs
- Ensure the server is started with:
  - `STREAM_PROGRESS=true` (default)
  - Optionally `AUGGIE_CLI=true` (enables INFO by default in the wrapper)
- Look for lines like:
  - `mcp_activity - INFO - [PROGRESS] analyze: Starting step 1/3 - ...`

### Auggie CLI
- Auggie launches the server via our wrapper; with `AUGGIE_CLI=true`, `LOG_LEVEL=INFO` is set by default
- Watch the CLI output or tail logs/logs/mcp_server.log for `[PROGRESS]` lines

### Logs
- Always available at `logs/mcp_server.log`
- Windows PowerShell: `Get-Content logs\mcp_server.log -Wait -Tail 50`

## Direct tool testing (no MCP client)

Use the included tool bench or in-process invocation to see progress:

- Planner (no model required):
  ```bash
  python scripts/tool_bench.py run planner --json "{\"step\":\"Create a small plan\",\"step_number\":1,\"total_steps\":1,\"next_step_required\":false,\"findings\":\"Testing\"}"
  ```
- ThinkDeep/Analyze (require models): set provider keys first, then run similar commands.

Quick smoke test runner:
```bash
python scripts/progress_test.py
```
This calls planner, thinkdeep, and analyze in-process via `server.handle_call_tool(...)` and prints results while the server logs `[PROGRESS]` breadcrumbs.

## Environment variables

- `STREAM_PROGRESS` (default: `true`): master switch for emitting progress
- `AUGGIE_CLI` (default: unset): when `true`, wrapper sets `LOG_LEVEL=INFO`
- `LOG_LEVEL` (default: `INFO` server-side): controls verbosity
- `LOG_FORMAT` (default: `json` server-side): set to `plain` for human-readable output

## Current limitations and next steps

- MCP-native notifications: the helper exposes `set_mcp_notifier`; when the python MCP SDK provides a stable notification API (e.g., `window/logMessage` or `$\progress`), we’ll wire it for richer UI surfacing in clients.
- Model-required tools won’t emit progress if they fail model validation early. Configure provider keys or use `planner` to validate progress in isolation.

## FAQ

- Q: I don’t see `[PROGRESS]` lines in VS Code. 
  - Ensure `STREAM_PROGRESS=true` and wrapper default to `INFO` is in effect or set `LOG_LEVEL=INFO` explicitly.
  - Check the extension Output channel and logs/mcp_server.log.
- Q: Can I disable progress?
  - Set `STREAM_PROGRESS=false`.

