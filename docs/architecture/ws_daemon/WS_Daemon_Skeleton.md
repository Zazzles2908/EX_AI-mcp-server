# WebSocket Daemon + stdio Shim (MCP) 

Date: 2025-09-09
Owner: EX-AI-MCP-Server

## Goals
- Support multiple concurrent applications connecting to MCP without stdio contention
- Keep VS Code Augment compatibility (stdio from the client’s perspective)
- Provide a shared, long-lived daemon to reduce RAM and keep caches warm
- Maintain strong local isolation and simple auth

## Scope (skeleton now, iterative hardening later)
- Loopback WebSocket daemon (ws://127.0.0.1:<port>) that multiplexes sessions
- Stdio shim that bridges JSON-RPC over stdio <-> WebSocket for VS Code
- Session manager with per-session quotas, logging, and graceful shutdown
- Health endpoint and minimal metrics (JSONL) in ./logs

## Transport & Protocol
- WebSocket text frames carrying JSON-RPC 2.0 messages (newline-safe JSON)
- Each client attaches an initial handshake: {type:"hello", session_id, auth_token?}
- The daemon tags/isolates per session_id; forwards tool calls to server core
- Backpressure: per-session queue limits (e.g., 32 inflight)

## Security
- Loopback only (127.0.0.1). Optional bearer token via EXAI_WS_TOKEN env
- Rotate token by restarting daemon; store token in shim env only
- Later: Windows Credential Manager integration if needed

## Process Model
- Daemon: one process. Single-instance guard via lock file at logs/ws_daemon.pid
- Client shim: one per MCP client/window; no global lock

## Dependencies (to confirm via EXAI)
- websockets (server + client) OR aiohttp (server) + websocket-client (client)
- Python 3.11+

## Files (proposed)
- src/daemon/ws_server.py            # WebSocket daemon (asyncio)
- src/daemon/session_manager.py      # Tracks sessions, quotas, routing
- src/daemon/router.py               # Minor routing/dispatch integration
- scripts/stdio_ws_shim.py           # Stdio<->WS bridge for VS Code MCP
- scripts/run_ws_daemon.py           # Run daemon locally (dev)
- scripts/run_ws_shim.py             # Launch shim (used by MCP config)
- docs/architecture/ws_daemon/WS_Daemon_Skeleton.md  # this doc

## Config
- EXAI_WS_PORT=8765 (default)
- EXAI_WS_TOKEN=<random>
- EXAI_WS_BACKPRESSURE=32
- LOG_LEVEL=INFO

## MVP Test Plan
1) Start daemon: `python -X utf8 scripts/run_ws_daemon.py`
2) Configure MCP client to run shim as the server command (stdio)
3) Open 2 VS Code windows; both connect through shim to single daemon
4) Verify basic tools work (listmodels, version, chat ping)
5) Check logs: one daemon process; two sessions; no contention

## Open Questions for EXAI
- Prefer websockets vs aiohttp for production stability on Windows? (memory, perf)
- Any pitfalls for JSON-RPC over WS (framing, long responses)?
- Minimal, safe auth approach for loopback? Token-only sufficient?
- Recommended backpressure defaults for Tier-2 Kimi + GLM rate limits?
- Health/metrics: what minimal counters/latency histograms are most useful?

## Risks
- New dependency; must manage lifecycle
- Session leaks if shims crash (add idle timeout)
- Rate limit spikes if multiple windows send heavy requests simultaneously

## Next Steps (once EXAI confirms)
- Implement daemon and shim skeletons (no heavy features)
- Add health and minimal metrics
- Integrate session_id tagging and quotas
- Validate with two VS Code windows concurrently

