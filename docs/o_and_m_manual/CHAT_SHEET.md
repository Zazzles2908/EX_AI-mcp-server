# EXAI‑MCP Chat Sheet (As‑Configured)

This cheat sheet captures how your EXAI‑MCP server will behave given your current .env and provides a fast operator reference plus a routing decision tree.

## Quick Start and Smoke
- Start server: `python -m server`
- Verify: call `status`, `version`, `listmodels`
- Smoke: `python tools/ws_daemon_smoke.py` (checks streaming, web‑cue, long‑context)
- Tail logs (PowerShell):
  - `Get-Content -Path logs\mcp_activity.log -Tail 200 -Wait`
  - `Get-Content -Path logs\mcp_server.log -Tail 200 -Wait`

## As‑Configured Behavior (from .env)
- Agentic routing: `DEFAULT_MODEL=auto`, `ROUTER_ENABLED=true`, `EX_ROUTING_PROFILE=balanced`
- Providers: KIMI and GLM enabled (keys present; allowlists set for safety)
- Long‑context bias: `WORKFLOWS_PREFER_KIMI=true`, `EX_PREFER_LONG_CONTEXT=true`
- Web search defaults ON: `EX_WEBSEARCH_ENABLED=true`, `EX_WEBSEARCH_DEFAULT_ON=true` (GLM/Kimi web browsing enabled)
- Lean tool surface: `LEAN_MODE=true`, `STRICT_LEAN=true` (core tools only)
- Expert pass off by default: `EXPERT_ANALYSIS_MODE=disabled`, `DEFAULT_USE_ASSISTANT_MODEL=false`
- WS daemon reachable: `EXAI_WS_HOST=127.0.0.1`, `EXAI_WS_PORT=8765`
- Structured logs + activity summaries: `LOG_FORMAT=json`, `EX_TOOLCALL_LOG_PATH=.logs/toolcalls.jsonl`, `EX_ACTIVITY_SUMMARY_AT_TOP=true`

Effect:
- Fast/default path = GLM `glm-4.5-flash`
- Web/time cues keep GLM preferred for browsing
- Long prompts bias Kimi/Moonshot; see thresholds below

## Routing Expectations
- Web/time cues (URL, "today", or `use_websearch=true`): prefer GLM browsing path
- Long‑context thresholds:
  - `estimated_tokens > 48k` → prefer Kimi/Moonshot
  - `estimated_tokens > 128k` → strongly prefer Kimi/Moonshot
- Vision/multimodal: prefer GLM (configurable)
- Default otherwise: GLM `glm-4.5-flash`

Note: Upstream prompt shaping may shorten effective text. To steer reliably, pass explicit `estimated_tokens` (the client wrapper now does this automatically).

## Hints and Field Defaults (Client Wrapper Enhancements)
- `estimated_tokens`: automatically injected from your prompt/messages before dispatch
- `continuation_id`: automatically tracked and propagated across multi‑step workflow calls
- Still recommended to set:
  - `use_websearch=true` when you want the browsing path
  - Include URLs or time‑sensitive wording for web cues

## Minimal Tool Examples (JSON‑style arguments)
- chat: `{ "prompt": "Summarize README", "model": "auto" }`
- thinkdeep (1 step): `{ "step": "Plan", "step_number": 1, "total_steps": 1, "next_step_required": false, "findings": "Kickoff" }`
- codereview: `{ "step": "Review", "step_number": 1, "total_steps": 1, "next_step_required": false, "findings": "Start", "relevant_files": ["/abs/path/file.py"] }`

## Logs to Watch
- `MCP_CALL_SUMMARY`: shows final `model`, `tokens`, `duration`
- Quick filters:
  - `Select-String -Path logs\mcp_activity.log -Pattern "MCP_CALL_SUMMARY"`
  - `Select-String -Path logs\mcp_server.log -Pattern "ERROR|Traceback"`

## Troubleshooting Quick Picks
1) Route surprises → Check `MCP_CALL_SUMMARY`; ensure `estimated_tokens` is large enough; include more raw text if needed
2) No tools → Confirm `LEAN_MODE/LEAN_TOOLS/STRICT_LEAN`
3) Streaming errors → Use `stream_demo` (async streaming path implemented)
4) Multi‑step validation → Always include step metadata (step, step_number, total_steps, next_step_required, findings)

## Decision Tree (Routing)
```mermaid
flowchart TD
    A[Tool call (model=auto)] --> B{Web/time cue? (use_websearch=true, URL, 'today')}
    B -- Yes --> G[Route to GLM browsing path]
    B -- No --> C{estimated_tokens > 128k?}
    C -- Yes --> H[Strongly prefer Kimi/Moonshot]
    C -- No --> D{estimated_tokens > 48k?}
    D -- Yes --> I[Prefer Kimi/Moonshot]
    D -- No --> E{Vision signal?}
    E -- Yes --> J[Prefer GLM (vision path)]
    E -- No --> F[Default GLM (glm-4.5-flash)]

    %% Notes
    subgraph Notes
    N1[estimated_tokens now sent by client wrapper]
    N2[LEAN_MODE=true restricts visible tools only]
    N3[Expert pass off by default; enable per-call if needed]
    end
```

## Acceptance Checks (Day‑1/Day‑2)
- stream_demo: fallback (zai) OK; streaming (moonshot) returns first chunk
- thinkdeep with a URL or `use_websearch=true`: completes and routes per rules
- chat_longcontext: executes; route depends on `estimated_tokens` (now injected)

## Safety & Defaults
- Secrets only in `.env` (never commit); `.env.example` documents placeholders
- Safe‑by‑default verification runs: linters/tests are OK without extra permission
- Expert second‑pass is OFF unless you request it per‑call

---

Maintained by EXAI‑MCP. Update this sheet when routing thresholds or provider preferences change.

