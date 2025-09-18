# Overview

## What this is
This manual explains, end to end, how to install, operate, and extend the EXAI-MCP server. It is written for beginners and operators who want a reliable, repeatable way to use the system.

## Who this is for
- New users evaluating EXAI-MCP
- Operators running day-to-day tasks (logs, health checks, smoke tests)
- Designers who want to understand the big-picture architecture and routing

## What you can do with EXAI-MCP
- Use a unified tool suite over MCP (stdio/WebSocket): chat, analyze, codereview, debug, refactor, tracer, testgen, precommit, planner, thinkdeep, secaudit, consensus, status, listmodels, version, stream_demo
- Route requests automatically to the most appropriate model (GLM manager by default; Kimi/Moonshot for long-context)
- Validate the server with smoke tests and structured logs (MCP_CALL_SUMMARY lines show model, tokens, duration)

## How it works (at a glance)
- Tools: individual capabilities exposed via MCP
- Provider Registry: knows which models are available and their capabilities
- IntelligentTaskRouter: chooses a model based on task cues (web, long-context, vision, etc.)
- Optional WebSocket shim/daemon: lets multiple MCP clients connect easily
- Logs: mcp_server.log (all activity) and mcp_activity.log (tool calls + summaries)

## Quick start
Prerequisites
- Python 3.9+
- Git
- At least one provider key in .env (KIMI_API_KEY or GLM_API_KEY)

Install
```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Add KIMI_API_KEY=... and/or GLM_API_KEY=...
```

Run the server
```
python -m server
```
Verify with an MCP client: call status, version, and listmodels.

## Example end-to-end session
1) Exploration (thinkdeep)
   - Ask: "Assess our repo’s architecture; list risks and quick wins"
   - Observe model in the log summary; web-cues may route to GLM, long-context to Kimi
2) Code review (codereview)
   - Provide the target file(s) and focus areas; confirm issues + suggestions
3) Routing demo (stream_demo)
   - Run fallback (non-stream) and streaming modes to validate provider connectivity

## FAQ (short)
- Why did it pick GLM when I expected Kimi?
  - If the prompt fit within GLM’s context window and no long-context hint was present, GLM stays preferred for speed.
- How do I force long-context?
  - Include a large prompt and/or set an explicit estimated_tokens hint via the calling tool; see Routing.
- How do I see what happened?
  - Check logs/mcp_activity.log for MCP_CALL_SUMMARY lines.

## Glossary
- MCP: Model Context Protocol (standard interface for tools/LLM servers)
- Routing hints: metadata such as long_context and estimated_tokens that bias model selection
- WS shim/daemon: a small wrapper to let multiple clients use the MCP server via WebSocket
