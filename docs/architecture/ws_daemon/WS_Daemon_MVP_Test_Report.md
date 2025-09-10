# WS Daemon + Stdio Shim MVP: Implementation & Test Report

## Overview
- Implemented a loopback WebSocket daemon (ws://127.0.0.1:8765 by default) that executes existing tools in-process by importing the current MCP server tool registry.
- Implemented a stdio shim that exposes a proper MCP stdio server using the official MCP SDK, and forwards list_tools/call_tool to the WS daemon.
- Goal: allow multiple independent clients/windows to connect concurrently via WS sessions while keeping VS Code compatibility through the shim.

## Components
- src/daemon/ws_server.py
  - WebSocket server using `websockets` (asyncio)
  - Auth via EXAI_WS_TOKEN (optional)
  - Ops: hello, list_tools, call_tool
  - Executes tools by calling `server.TOOLS[name].execute(arguments)`
- src/daemon/session_manager.py
  - Minimal session registry and inflight counters (extensible)
- scripts/run_ws_daemon.py
  - Entry point to launch the WS daemon
- scripts/run_ws_shim.py
  - MCP stdio server (using `mcp.server`) bridging to WS daemon
  - For each MCP request, forwards to the daemon and adapts results
- tools/ws_daemon_smoke.py
  - Simple smoke test that opens two WS clients and runs list_tools + version

## Configuration
Environment variables (defaults):
- EXAI_WS_HOST=127.0.0.1
- EXAI_WS_PORT=8765
- EXAI_WS_TOKEN= (empty => no auth)
- EXAI_WS_MAX_BYTES=33554432 (32MB)
- EXAI_WS_PING_INTERVAL=25
- EXAI_WS_PING_TIMEOUT=10

## Install
- Added dependency: `websockets==12.0` (installed into .venv)

## How to run (local)
1) Start the daemon
   - `python scripts/run_ws_daemon.py`
2) (Optional) Run smoke test
   - `python tools/ws_daemon_smoke.py`
   - Expected: two clients show ~21 tools and version output for each
3) Start the shim (for VS Code Augment)
   - Configure your MCP server command to: `python scripts/run_ws_shim.py`
   - The shim presents a normal MCP stdio server to the client

## Test Results (on Windows 11)
- Daemon started: ws://127.0.0.1:8765
- Smoke test output (two clients concurrently):
  - Tools count: 21 for both clients
  - Version tool ran successfully for each client
- This validates multi-client concurrency against a single shared daemon instance

## Notes & Next Steps
- Backpressure/quotas: currently minimal; defaults are good for Tier-2 but can be tuned
- Health/metrics: log files are written by the main server; adding daemon-specific health.json/metrics.jsonl is a small follow-up
- Security: EXAI_WS_TOKEN supported; for enterprise, consider Windows Named Pipes or mTLS on loopback
- Productionization: add reconnection in shim, rotation of token, idle session GC, and circuit breaking for 429/5xx

## Mapping to EXAI Guidance
- Libraries: `websockets` for server+client
- Framing: 1 JSON message per WS frame; 32MB limit; ping/pong as configured
- Local auth: token in hello
- Quotas: ready to add; defaults align with guidance
- MVP Steps: implemented daemon, shim, config, and smoke tests

