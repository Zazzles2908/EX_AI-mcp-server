# Architecture

> Deprecation: legacy module paths `providers.*` and `routing.*` are shims; prefer `src.providers.*` and `src/router/*` (plus `src/core/agentic/*`).


## Module map (where things live)
- tools/: each MCP tool implementation (chat, analyze, codereview, thinkdeep, etc.)
- tools/registry.py: maps tool names to module/class, supports LEAN_MODE allowlists
- src/router/service.py: Service-level routing integration

- src/providers/: provider implementations and registry (providers/* is a deprecated shim)
- src/providers/registry.py: lists models, provider capabilities, and builds fallback chains
- src/core/agentic/task_router.py: IntelligentTaskRouter and helpers (signals, thresholds)
- logs/: output logs (mcp_server.log, mcp_activity.log)

## Data flow (text only diagram)
```
Client → MCP tool call (args) → Tool (SimpleTool/Base) → Routing hints
      → Provider Registry (models, capabilities) → IntelligentTaskRouter
      → Selected provider/model → Provider SDK call → Response
      → Tool formats result → Logs (TOOL_CALL/COMPLETED, MCP_CALL_SUMMARY)
```

## IntelligentTaskRouter (what it looks at)
Inputs
- Tool-level metadata (e.g., use_websearch, images present)
- estimated_tokens (explicit) and/or prompt length estimation
- Hints from tool layer: long_context, vision, deep, etc.
- Environment preferences (e.g., WORKFLOWS_PREFER_KIMI)

Selection rules (current defaults)
- Default fast manager: GLM (glm-4.5-flash)
- Web/time cues (URLs, "today", use_websearch): prefer GLM browsing path
- Long-context: if estimated_tokens > 48k, prefer Kimi/Moonshot (context window bias)
- Very long-context: > 128k strongly prefer Kimi/Moonshot
- Vision/multimodal: prefer GLM (configurable)

Why long-context sometimes still routes to GLM
- Upstream prompt shaping may reduce the effective prompt before routing
- GLM context window can be large enough; when it fits, GLM remains competitive for latency

## Provider Registry (fallback chains)
- Discovers available models from env keys
- Orders candidates by suitability (context window, feature flags, preferences)
- When long_context hint is present: sort primarily by context window and long-context preference

## Observability
- mcp_activity.log: concise markers for each tool call with summaries
- mcp_server.log: detailed diagnostics and stack traces if any
- Smoke script (tools/ws_daemon_smoke.py): validates end-to-end connectivity and routing cues

## WebSocket shim/daemon (optional)
- Purpose: expose the server over WS so multiple clients can attach
- Benefit: easy live manual tests from tools and GUI clients

## Future-proofing
- Toggle to hard-prefer Kimi/Moonshot for long-context regardless of GLM capacity
- Provider-native tokenization to improve estimated_tokens accuracy
- Cost/latency-aware policies (budget/SLA driven)
