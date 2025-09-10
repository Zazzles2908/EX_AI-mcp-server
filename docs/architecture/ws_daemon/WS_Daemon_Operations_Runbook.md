# WS Daemon + Stdio Shim: Operations Runbook

This runbook documents how to operate the multi‑client WebSocket daemon with a stdio shim for MCP clients. It covers:
- Architecture overview and supported clients
- Environment variables and defaults
- Start/stop, health and metrics
- MCP client configuration examples for:
  - Auggie CLI
  - Augment Code (VS Code)
  - Claude application (generic MCP client config)
- Auth rotation, concurrency/backpressure tuning
- Troubleshooting checklist

## 1) Architecture overview
- A single shared daemon runs on loopback WebSocket (default ws://127.0.0.1:8765).
- Each client (VS Code window, CLI, Claude app) runs a lightweight stdio shim process.
- The shim speaks MCP stdio to its client and forwards JSON‑RPC to the daemon over WebSocket.
- The daemon executes MCP tools in‑process via the server.handle_call_tool boundary, ensuring consistent model/provider routing and safeguards.

Key properties:
- Multi‑client concurrency with per‑session and global backpressure
- Local‑only auth token (optional) via EXAI_WS_TOKEN
- Heartbeats, per‑call timeouts, and JSONL metrics

## 0) Quick Start (no tokens, simplest path)
If you didn’t set EXAI_WS_TOKEN, authentication is disabled and setup is very simple. Follow these steps exactly.

Step A — Keep the daemon running
- Open Terminal 1 in the repo root: C:/Project/EX-AI-MCP-Server
- Run:
  - C:/Project/EX-AI-MCP-Server/.venv/Scripts/python.exe scripts/run_ws_daemon.py
- Expected output includes:
  - ws_daemon - INFO - Starting WS daemon on ws://127.0.0.1:8765
  - websockets.server - INFO - server listening on 127.0.0.1:8765

Step B — Connect VS Code (Augment Code)
- Create a file at the repo root (same folder as scripts/): mcp-config.augmentcode.json
- Paste this minimal config (no token needed):
```
{
  "servers": {
    "exai-mcp": {
      "command": "C:/Project/EX-AI-MCP-Server/.venv/Scripts/python.exe",
      "args": ["scripts/run_ws_shim.py"],
      "cwd": "C:/Project/EX-AI-MCP-Server",
      "env": {
        "EXAI_WS_HOST": "127.0.0.1",
        "EXAI_WS_PORT": "8765",
        "EXAI_SHIM_RPC_TIMEOUT": "30"
      }
    }
  }
}
```
- In VS Code:
  1) Command Palette (Ctrl+Shift+P) → Augment: Restart MCP Servers
  2) Open Augment panel → confirm server appears (green/healthy)
  3) Run tool “version” (or “listmodels”) to verify
- Alternatively, we already added an entry named "EXAI-WS" to mcp-config.augmentcode.json. In Augment, select the MCP server profile "EXAI-WS" if your UI lists profiles from this file.


Step C — (Optional) Connect Auggie CLI
- Use the same command/args/cwd/env as above for the CLI’s MCP server profile.
- Select server id exai-mcp and run a simple tool like version.

Step D — (Optional) Connect Claude
- If your Claude app supports adding MCP stdio servers:
  - Command: C:/Project/EX-AI-MCP-Server/.venv/Scripts/python.exe
  - Args: ["scripts/run_ws_shim.py"]
  - Working dir: C:/Project/EX-AI-MCP-Server
  - Env: EXAI_WS_HOST=127.0.0.1, EXAI_WS_PORT=8765, EXAI_SHIM_RPC_TIMEOUT=30
- If your Claude app supports direct WebSocket MCP (advanced), connect to ws://127.0.0.1:8765 and send a hello without token.

Notes
- Always prefer the absolute Python path above to avoid PATH issues.
- If you change EXAI_WS_PORT, update it in the client env as well.
- No token = anyone on this machine can connect via loopback. For personal/dev boxes this is typically fine; set a token later for extra protection.

## 2) Environment variables (daemon)
- EXAI_WS_HOST: 127.0.0.1
- EXAI_WS_PORT: 8765
- EXAI_WS_TOKEN: (optional local bearer; empty disables auth)
- EXAI_WS_MAX_BYTES: 33554432 (32 MB frame limit)
- EXAI_WS_PING_INTERVAL: 25 (seconds)
- EXAI_WS_PING_TIMEOUT: 10 (seconds)
- EXAI_WS_CALL_TIMEOUT: 120 (seconds per tool call)
- EXAI_WS_SESSION_MAX_INFLIGHT: 8 (per session concurrent calls)
- EXAI_WS_GLOBAL_MAX_INFLIGHT: 24 (global concurrent calls)
- EXAI_WS_KIMI_MAX_INFLIGHT: 6 (global cap for Kimi provider)
- EXAI_WS_GLM_MAX_INFLIGHT: 4 (global cap for GLM provider)
### 2.1) Using .env safely
If you keep values in a `.env` file, avoid inline comments and extra spaces after `=` because most loaders treat them as part of the value. Use one of these patterns:

Valid examples:
```
EXAI_WS_HOST=127.0.0.1
EXAI_WS_PORT=8765
EXAI_WS_TOKEN=
EXAI_WS_MAX_BYTES=33554432
EXAI_WS_PING_INTERVAL=25
EXAI_WS_PING_TIMEOUT=10
EXAI_WS_CALL_TIMEOUT=120
EXAI_WS_SESSION_MAX_INFLIGHT=8
EXAI_WS_GLOBAL_MAX_INFLIGHT=24
EXAI_WS_KIMI_MAX_INFLIGHT=6
EXAI_WS_GLM_MAX_INFLIGHT=4
```

Avoid this (will break parsing):
```
EXAI_WS_MAX_BYTES= 33554432 #(32 MB frame limit)
EXAI_WS_TOKEN = #(optional)
```
If you need comments, put them on their own line starting with `#`.


## 3) Environment variables (shim)
- EXAI_WS_HOST/PORT/TOKEN must match daemon
- EXAI_SHIM_RPC_TIMEOUT: 30 (seconds; shim waits for a tool response before retrying once)

## 4) Start/Stop
- Start daemon (from repo root):
  - Windows: `python scripts\run_ws_daemon.py`
- Stop: Ctrl+C in the daemon terminal.
- Logs:
  - Health snapshot: `logs/ws_daemon.health.json`
  - Metrics JSONL: `logs/ws_daemon.metrics.jsonl`
  - MCP server logs: `logs/mcp_server.log`

## 5) Health and metrics
- Health snapshot includes timestamp, session count, global capacity, approximate inflight.
- Metrics JSONL appends per tool call: timestamp, latency, session id, tool name, provider tag (if detected).
- Use these to detect hot spots and tune concurrency caps.

## 6) MCP client configuration examples

### 6.1) Auggie CLI (generic MCP client)
- Configure the CLI to start the shim as the MCP server command.
- Example (pseudo‑config):
```
{
  "servers": {
    "exai-mcp": {
      "command": "python",
      "args": ["scripts/run_ws_shim.py"],
      "cwd": "C:/Project/EX-AI-MCP-Server",
      "env": {
        "EXAI_WS_HOST": "127.0.0.1",
        "EXAI_WS_PORT": "8765",
        "EXAI_WS_TOKEN": "<optional-token>",
        "EXAI_SHIM_RPC_TIMEOUT": "30"
      }
    }
  }
}
```
- Then point Auggie CLI to the server id `exai-mcp`.

### 6.2) Augment Code (VS Code extension)
- mcp-config.augmentcode.json entry for the shim (example Windows paths):
```
{
  "servers": {
    "exai-mcp": {
      "command": "python",
      "args": ["scripts/run_ws_shim.py"],
      "cwd": "C:/Project/EX-AI-MCP-Server",
      "env": {
        "EXAI_WS_HOST": "127.0.0.1",
        "EXAI_WS_PORT": "8765",
        "EXAI_WS_TOKEN": "<optional-token>",
        "EXAI_SHIM_RPC_TIMEOUT": "30"
      }
    }
  }
}
```
- In Augment settings, select this MCP server profile.

### 6.3) Claude application (generic MCP client)
- Many MCP clients accept a JSON config for external servers. Use the same shim command pattern:
```
{
  "servers": {
    "exai-mcp": {
      "command": "python",
      "args": ["scripts/run_ws_shim.py"],
      "cwd": "C:/Project/EX-AI-MCP-Server",
      "env": {
        "EXAI_WS_HOST": "127.0.0.1",
        "EXAI_WS_PORT": "8765",
        "EXAI_WS_TOKEN": "<optional-token>",
        "EXAI_SHIM_RPC_TIMEOUT": "30"
      }
    }
  }
}
```
- If your Claude app supports direct WebSocket MCP transport, you can connect to ws://127.0.0.1:8765 using the `hello` handshake with the `token` field set to `EXAI_WS_TOKEN`.

## 7) Auth rotation (local)
- Rotate the daemon token without restart by sending an admin op over WS:
  - Request: `{ "op": "rotate_token", "old": "<current>", "new": "<next>" }`
  - On success, the daemon accepts only the new token for new connections; existing sessions remain until they disconnect.
- After rotation, update each client’s EXAI_WS_TOKEN and reconnect.

## 8) Concurrency/backpressure tuning
- Defaults suit a Tier‑2 environment:
  - Per session: 8
  - Global: 24 (increase to 32 if stable)
  - Provider caps: Kimi 6, GLM 4
- Behavior on saturation: clients receive a structured `OVER_CAPACITY` error to retry with backoff.
- If bursts are common, consider per‑session queues (not enabled by default in this build).

## 9) Troubleshooting
- Client fails to connect
  - Ensure daemon is running and listening on 127.0.0.1:8765
  - Token mismatch: verify EXAI_WS_TOKEN matches in shim and daemon
  - Port conflict: change EXAI_WS_PORT
- Calls hang or time out
  - Check global/session/provider caps; lower concurrency or increase EXAI_WS_CALL_TIMEOUT
  - Inspect logs/ws_daemon.metrics.jsonl for slow tools
- Multiple windows interfere
  - Each window should spawn its own shim; this is expected and supported
- Rapid connect/disconnect loops
  - Inspect logs/mcp_server.log for exceptions
  - Temporarily disable auth to isolate issues

## 10) Runbook: typical operations
1. Set env (optional): EXAI_WS_TOKEN, concurrency caps
2. Start daemon: `python scripts/run_ws_daemon.py`
3. Configure clients to use the shim command as their MCP server
4. Validate with two concurrent clients (VS Code windows or CLI)
5. Monitor health.json and metrics.jsonl; adjust caps if needed
6. Rotate token periodically if required; reconnect clients

## 11) Notes and future hardening
- Named Pipes or mTLS on loopback for enterprise deployments
- Optional subprocess sandbox for heavy tools
- Log rotation for metrics JSONL when the file grows large

