# WS Smoke Test (exai-ws)

Use this to verify the WebSocket daemon end-to-end and debug auth/connection issues quickly.

## Env required
- EXAI_WS_HOST (default 127.0.0.1)
- EXAI_WS_PORT (default 8765)
- EXAI_WS_TOKEN (required if the daemon enforces auth)

## Quick run
```bash
python scripts/ws_exercise_all_tools.py
```

- Prints tool list and then exercises each tool with minimal safe args
- Exits 0 when all non-provider tools succeed

## Common errors and fixes
- unauthorized: The daemon requires a token but the client didn’t send the correct one.
  - Ensure both sides agree on EXAI_WS_TOKEN
  - Restart daemon after changing .env
- connection failed: Daemon not running or host/port mismatch
  - Check EXAI_WS_HOST/EXAI_WS_PORT and firewall

## Alternate run (no token)
If your daemon allows anonymous access, run the no-auth wrapper:
```bash
python scripts/ws_exercise_all_tools_noauth.py
```

## Logs to check
- logs/mcp_server.log (server-side)
- .logs/toolcalls.jsonl (tool-call JSONL if enabled)


