# EX MCP Server - Rebrand & MCP-First Notes

This document tracks the high-impact rebranding and architectural adjustments.

- Package name: `ex-mcp-server` (was `zen-mcp-server`)
- Console script: `ex-mcp-server` (was `zen-mcp-server`)
- Server identity defaults:
  - MCP_SERVER_NAME default: "EX MCP Server"
  - MCP_SERVER_ID default: "ex-server"
- Logs/stderr tag: `[ex-mcp]` (was `[zen-mcp]`)
- Remote mode: kept optional via `remote_server.py` (FastAPI/SSE)
- Test bench: `scripts/tool_bench.py` for direct tool invocation
- MCP-first: standalone run scripts deprecated (retain for legacy docs if needed)

Validation checklist:
- [ ] No "zen" references remain (search case-insensitive)
- [ ] MCP clients display "EX MCP Server"
- [ ] Stdio transport remains primary; remote mode optional only
- [ ] Tools invocable via tool bench
- [ ] Provider integrations verified (KIMI, GLM, OpenRouter, Custom)

