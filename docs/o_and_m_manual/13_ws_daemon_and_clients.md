# WS Daemon & Clients

## WS shim/daemon purpose
- Expose the MCP server over WebSocket so multiple clients can attach simultaneously
- Useful for manual smoke tests and GUI client validation

## Data flow
server (stdio) <-> WS shim (daemon) <-> clients (Claude Desktop, VSCode Augment)

## Smoke script
```
python tools/ws_daemon_smoke.py
```
Validates:
- Tool visibility; provider health
- stream_demo fallback+stream
- thinkdeep web-cue
- chat_longcontext execution

## Client setup quick notes
- Claude Desktop: add a custom MCP server pointing to the WS shim URL
- VS Code (Augment extension): configure the extension to use the shim URL (Windows-friendly)

## Connectivity triage
- 404/connection refused: check shim URL/port and that base server is up
- Works for one client only: confirm shim accepts multiple connections
- Stale state after updates: restart daemon and client, then rerun smoke

## Logs
- mcp_activity.log: verify tool calls reach the server
- mcp_server.log: provider errors or exceptions if any

