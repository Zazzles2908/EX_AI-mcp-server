## EXAI Toolkit — Current Capabilities (2025-09-10)

### Overview
EXAI is running in EXAI-WS mode (stdio shim bridging a local WebSocket daemon). The shim uses the latest MCP stdio stream API and a unified .env configuration. The daemon exposes the same tool registry as the classic server while adding concurrency controls and health telemetry.

- Server: EX MCP Server 5.8.5 (Windows)
- Providers: Kimi (Moonshot) ✅, GLM (ZhipuAI) ✅
- Models available: 18 (Kimi + GLM)
- Single source of truth for configuration: C:/Project/EX-AI-MCP-Server/.env
- Logs: logs/mcp_server.log, logs/mcp_activity.log, logs/ws_daemon.health.json, logs/ws_shim.log

### Architecture (WS daemon + stdio shim)
- VS Code/clients launch shim over stdio
- Shim connects to local WS daemon (127.0.0.1:8765)
- Daemon validates calls, enforces backpressure, dispatches to server tools
- Health/metrics written to logs/ws_daemon.health.json and metrics JSONL

### Confirmed Providers & Models
- KIMI_API_KEY present → Kimi models (e.g., kimi-k2-0905-preview, kimi-k2-turbo-preview, moonshot-v1-*).
- GLM_API_KEY present → GLM models (glm-4.5-flash, glm-4.5, glm-4.5-air).
- Total advertised models: 18 (listmodels).

### Tool Registry (EXAI-WS)
Registered tools per provider_capabilities:
activity, analyze, challenge, chat, codereview, consensus, debug, docgen,
kimi_chat_with_tools, kimi_upload_and_extract, listmodels, orchestrate_auto,
planner, precommit, provider_capabilities, refactor, secaudit, testgen,
thinkdeep, tracer, version.

### Current Status by Evidence
Below reflects tool behavior validated via EXAI calls and activity logs.

- Working (TOOL_COMPLETED evidence and/or outputs captured):
  - version, listmodels, provider_capabilities, activity
  - chat, thinkdeep, planner, challenge
  - analyze, codereview, debug
  - docgen, precommit, refactor
  - tracer

- Partial:
  - consensus → Works with explicit model; failed when invoked with model="auto". Use a concrete model (e.g., glm-4.5-flash or a kimi-*).

- Pending capture / Re-run recommended individually:
  - orchestrate_auto, kimi_chat_with_tools, kimi_upload_and_extract, secaudit, testgen
  (These are registered; outputs did not get captured in the last pass. Re-running individually should produce results.)

### Health & Smoke Evidence
- tools/ws_daemon_smoke.py → tools count: 21 for two concurrent clients; version returned banner.
- logs/ws_daemon.health.json → shows fresh timestamps and expected capacity fields.
- logs/mcp_activity.log → multiple TOOL_CALL/TOOL_COMPLETED lines for chat, thinkdeep, analyze, codereview, debug, docgen, precommit, refactor, tracer, etc.

### Recommended Client Configs (examples updated)
The following examples are provided and updated to the unified .env approach, unbuffered Python, and UTF‑8:

- docs/architecture/ws_daemon/examples/auggie.mcp.json
- docs/architecture/ws_daemon/examples/claude.mcp.json

Key settings:
- command: .venv/Scripts/python.exe
- args: ["-u", "C:/Project/EX-AI-MCP-Server/scripts/run_ws_shim.py"]
- cwd: C:/Project/EX-AI-MCP-Server
- env: {
  ENV_FILE=.env,
  EXAI_WS_HOST=127.0.0.1,
  EXAI_WS_PORT=8765,
  EXAI_SHIM_RPC_TIMEOUT=30,
  PYTHONIOENCODING=utf-8,
  PYTHONUNBUFFERED=1,
  LOG_LEVEL=INFO
}

### How to Verify Quickly
1) Toggle the EXAI-WS server OFF/ON in client, or reload the window.
2) Run version and listmodels.
3) Call chat (glm-4.5-flash) and thinkdeep (minimal mode) to confirm.

### Troubleshooting Notes
- If a tool appears missing in the client UI, check Output → Augment (or Augment MCP) and logs/ws_shim.log for initialization errors.
- For consensus, avoid model="auto"; specify a concrete model.
- Ensure .env contains at least one provider key (KIMI_API_KEY or GLM_API_KEY).

### Next Steps
- Individually re-run pending tools (orchestrate_auto, kimi_* tools, secaudit, testgen) to capture outputs and update this report.
- If needed, add provider‑specific usage notes under toolkit/ for each complex tool.

