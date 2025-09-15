# EX MCP Architecture Overview

**Updated**: 2025-01-13
**Status**: Production with Advanced Context Manager Integration

Comprehensive overview of how EX MCP is architected, how tools execute, and how the Advanced Context Manager optimizes performance.

## 1) Entry & Transports
- Stdio MCP (default): server.py exposes tools via the MCP protocol over stdio.
- Remote HTTP/SSE (optional): remote_server.py exposes the same tools at /mcp (+ /sse, /v1/sse) using FastAPI.

## 2) Tool discovery & dispatch
- tools/registry.py registers every tool with a name (e.g. analyze_exai, planner_exai, thinkdeep_exai).
- server.py receives a tool name + args, loads the tool from the registry, and executes it.
- Two families:
  - Simple tools: tools/simple/base.py — single-shot, return content immediately
  - Workflow tools: tools/workflow/base.py — multi-step semantics (status like *_in_progress, pause_for_*, continuation_available)

## 3) Progress & visibility
- Tools call utils/progress.send_progress("…") which logs [PROGRESS] messages.
- server.py captures these during the tool call and injects them into the JSON result as `metadata.progress` so UIs can show a dropdown of steps.
- If you don't see the dropdown: ensure the primary content is JSON text and that progress is attached (we now attach for all statuses).

## 4) Model routing
- providers/registry.py lists available providers (KIMI/GLM/OpenRouter/custom, etc.).
- tools/models.py and utils/model_context.py help resolve {model name -> provider, base URL, api key}.
- A tool chooses a model via its parameters or defaults (e.g., thinkdeep_exai may default to Kimi unless overridden). You can pass model/provider overrides in the tool args.

## 5) Response shape
- Simple tools return a list of contents (usually one TextContent with JSON string).
- Workflow tools return status fields (e.g., analyze_in_progress, continuation_available); server still injects `metadata.progress`.

## 6) Remote auth & CORS
- Remote server enforces `Authorization: Bearer MCP_AUTH_TOKEN` when set.
- CORS_ORIGINS controls which browser/hosts can call it (use * only for testing).

## 7) Where to look in code
- server.py — stdio MCP, progress capture, response shaping
- remote_server.py — HTTP/SSE adapter
- tools/registry.py — tool list and binding
- tools/simple/base.py & tools/workflow/base.py — execution semantics
- providers/registry.py — model providers
- utils/model_context.py — model resolution
- utils/progress.py — progress emission

## 8) Overriding model per tool
- Pass explicit params when calling a tool (e.g., model: "glm-4.5-flash" or provider: "openrouter").
- The provider registry resolves the endpoint and credentials accordingly.

## 9) Minimal mental model
1) Client sends: {tool_name, args}
2) server.py looks up tool → runs it
3) Tool emits progress → server captures
4) Tool calls model via selected provider
5) server.py returns JSON with result + metadata.progress for UI visibility

## 10) How progress appears in VS Code
- Primary: UI parses `metadata.progress` to show a dropdown in the chat tool-call row
- Fallback (we enabled): server also appends a text block labeled `=== PROGRESS === ...` so you can read steps even if the UI doesn’t render the dropdown yet


