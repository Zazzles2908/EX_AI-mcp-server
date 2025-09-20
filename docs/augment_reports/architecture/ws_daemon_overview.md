# WS Daemon & Transport Overview (Augment)

Status: Updated 2025-09-20

WS stack (per mcp-config)
- Shim command: .venv/Scripts/python.exe -u scripts/run_ws_shim.py
- Host/Port: 127.0.0.1:8765 (no token required per current .env)
- Env highlights:
  - EXAI_WS_HOST / EXAI_WS_PORT
  - EXAI_SHIM_RPC_TIMEOUT (default 150s)
  - EX_SESSION_SCOPE_STRICT=true; EX_SESSION_SCOPE_ALLOW_CROSS_SESSION=false

Payload delivery guard (fix applied)
- Symptom (historical): empty payloads from tools (ThinkDeep/Analyze) even with MICROSTEP=true
- Root cause: diagnostic stub used JSON booleans in Python block; exception swallowed → empty
- Fix: Use Python booleans, add EX_ENSURE_NONEMPTY_FIRST=true to force non-empty first block
- Expected behavior:
  - If tool returns nothing → diagnostic stub appears: {status=no_payload_from_tool, diagnostic_stub=true}
  - With MICROSTEP=true → first block shows analysis_partial draft, then continuation

Validation steps (quick)
1) chat_EXAI-WS ping: prompt "MCP ping: reply exactly 'OK'" → expect OK
2) listmodels/provider_capabilities (tools) → expect providers from src/providers
a) Optional: ROUTER_DIAGNOSTICS_ENABLED=true and ROUTER_LOG_LEVEL=INFO
   - Observe logs/router entries: route_diagnostics, route_decision
3) thinkdeep_EXAI-WS minimal run → verify non-empty first block

Troubleshooting
- If empty blocks persist: confirm EX_ENSURE_NONEMPTY_FIRST=true and check logs/mcp_server.log for diagnostic lines
- If model alias errors: avoid DEFAULT_MODEL=auto during audits; pin glm-4.5-flash or kimi-* explicitly

