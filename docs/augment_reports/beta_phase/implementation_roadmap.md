## Top-line (YES/NO)
YES — A phased plan will stabilize reliability immediately (P0), extend resilience and consistency (P1), complete reorg and cleanups (P2), and add optional deep diagnostics (P3).

## Phase Overview and Priorities
- P0 (Stabilize now): Dispatcher fallback for file_chat, local hardening for Kimi multi-file chat, standardized error envelopes.
- P1 (System resilience): Extend fallback to chat_with_tools and chat; add circuit breakers; unify error semantics across tools.
- P2 (Reorg + compliance): Modularize server.py, complete scripts reorg with wrappers, finish tool description/visibility cleanup.
- P3 (Provider depth + diagnostics): Moonshot API feature alignment (file-based QA, context caching, tool-calls), GLM native SDK migration, optional MoonPalace traces.

## Dependencies and Sequencing
- P0 has no external dependencies; delivers immediate user-visible improvements.
- P1 depends on P0 error envelope format and dispatcher hooks.
- P2 depends on P1 minimal stability to safely refactor; wrappers ensure no breakage.
- P3 depends on P2 modular seams for clean provider integrations and experiments.

## Detailed Plan

### P0 — Immediate Stabilization (1–2 days)
1) Dispatcher Fallback Orchestrator (server.py)
- Add a small orchestrator around handle_call_tool:
  - Map capabilities to fallback chains:
    - file_chat: [kimi_multi_file_chat → glm_multi_file_chat → analyze(files→summary) → chat]
    - chat_with_tools: [kimi_chat_with_tools → glm chat with tools (if available) → chat]
    - plain_chat: [preferred provider → alternate provider → chat-minimal]
  - Per-attempt time budget and classification (timeout, cancellation, provider_error).
  - JSONL attempt breadcrumbs: {attempt, tool, provider, elapsed, outcome, next}.
  - Respect circuit-breaker state (initially a no-op toggle until P1).

2) Harden KimiMultiFileChatTool
- Add per-call timeout env KIMI_MF_CHAT_TIMEOUT_SECS (default 180s) and 1 retry with exponential backoff.
- On error/timeout, return a structured envelope (not raw exception):
  {"status":"execution_error","error_class":"timeout|provider_error","provider":"KIMI","tool":"kimi_multi_file_chat"}
- Keep existing upload-and-extract flow unchanged in P0 (minimize blast radius).

3) Standardize Error Envelopes (shared helper)
- A tiny helper that tools use to emit consistent structured failures.
- Fields: status, error_class, provider, model, tool, attempt (optional), req_id (propagated from dispatcher).

4) Tests/Validation
- Run scripts/validation/ws_exercise_all_tools.py and backend runner with unpredictable prompts.
- Expect: no hangs; clear fallbacks; artifacts recorded.

### P1 — System Resilience (1–2 days)
1) Extend Fallback Chains
- Apply same fallback pattern to chat_with_tools and plain chat.
- Optionally add websearch-specific branches (e.g., Kimi websearch → GLM websearch → local DuckDuckGo backend).

2) Circuit Breakers + Cool-offs
- Per provider/model rolling window (in-memory):
  - Trip on N failures in M minutes; skip attempts during cool-off; half-open probes.
  - Record breaker state transitions in JSONL + activity logs.

3) Tool Unification
- Update kimi_chat_with_tools and glm multi-file chat to use structured envelopes and common timeout semantics.
- Normalize streaming vs non-streaming behavior for consistent failure surface.

4) Validation
- Stress-run with randomized prompts and files; verify breaker trips route away from failing paths without user-visible errors.

### P2 — Server Modularization + Scripts Reorg (2–3 days)
1) Server Modularization (proposed structure)
- src/server/
  - orchestrator.py (entry wrapper for handle_call_tool)
  - dispatcher.py (tool lookup, request shaping)
  - fallback.py (fallback chains, attempt loop)
  - circuit.py (circuit-breakers)
  - telemetry.py (JSONL breadcrumbs, mcp_activity integration)
  - conversations.py (continuation_id handling)
  - registry_bridge.py (TOOLS exposure + visibility tiers)
- server.py remains as thin glue importing from src/server/*.

2) Scripts Reorganization (non-destructive)
- Canonical folders: validation/, diagnostics/, ws/, e2e/, tools/, kimi_analysis/, legacy/.
- Leave tiny wrappers at old paths that forward to new modules and print the new canonical location.
- Update README.md within each folder with purpose, common commands, and example invocations.

3) Tool Description/Visibility Cleanup
- Finish removing manager-specific vocabulary; maintain tiers: user-facing, manager-only, backend pathway.

4) Validation
- Run ws and e2e scripts from new paths; wrappers ensure no breakage.

### P3 — Provider Integration Depth + Diagnostics (3–5 days)
1) Moonshot (Kimi) Compliance
- Read and implement patterns from docs:
  - Multi-turn conversations via Kimi API
  - Tool-calls semantics (names, arguments, return mapping)
  - File-based QA: prefer file-id attachment / native mechanisms
  - Context caching feature: use cache tokens consistently (we already add headers; ensure full handshake)
- Fix Kimi multi-file cancellations at the root by switching to provider-preferred patterns:
  - Where supported, pass file ids/context-caching tokens rather than raw extracted text.
  - Validate message schemas and tool choice objects match docs.

2) GLM Native SDK Migration (zai-sdk)
- Replace OpenAI-like abstractions with native endpoints:
  - Web Search API: docs.z.ai/guides/tools/web-search
  - File Upload API: docs.z.ai/api-reference/agents/file-upload
  - Agent/Conversation APIs for multi-turn + async polling
- Implement minimal adapters to keep MCP contracts stable while using native SDK features.

3) Optional MoonPalace Diagnostic Mode
- Dev flag to route Kimi calls through MoonPalace for deep traces; write artifacts under docs/augment_reports/augment_review_02/kimi_analysis/runs/.
- Disabled by default; not in main runtime path.

## Fallback Orchestrator Design (details)
- Capability → Chain map (configurable, with env overrides for ordering).
- Attempt loop:
  - Execute tool with per-attempt timeout;
  - On structured failure (status, error_class), classify and continue;
  - Respect circuit-breaker state;
  - Record JSONL breadcrumb with attempt outcome and next fallback.
- Final response always returns a best-effort answer (from last successful attempt) or a comprehensive error summary with guidance.

## Standardized Error Envelope (spec)
```json
{
  "status": "execution_error",
  "error_class": "timeout|provider_error|cancelled|unsupported",
  "provider": "KIMI|GLM|unknown",
  "model": "<model>",
  "tool": "<tool_name>",
  "attempt": 1,
  "req_id": "<uuid>",
  "detail": "human-readable short description"
}
```

## Testing & Validation Strategy
- Unit tests around fallback and circuit logic (simulate tool results and failures).
- Integration tests via ws_exercise_all_tools and backend runner with unpredictable prompts.
- Golden-path checks for UI visibility and no silent drops; compare raw frames to UI outputs.
- Provider-specific smoke: small files + constrained prompts to validate cancellation is resolved (Kimi), uploads + chat (GLM).

## Risk Mitigation
- P0 changes are additive and localized (orchestrator wrapper + tool hardening) — low risk.
- P2 modularization: keep server.py thin and compatible; wrappers for scripts prevent breaking workflows.
- P3 provider shifts: guard with feature flags; keep OpenAI-compatible paths available during transition.

## Resource Estimates
- P0: 1–2 engineer-days
- P1: 1–2 engineer-days
- P2: 2–3 engineer-days
- P3: 3–5 engineer-days (docs study, SDK migration, optional MoonPalace)

## Backward Compatibility
- MCP tool contracts preserved; responses now include consistent envelopes and optional fallback metadata.
- Scripts callable from old paths via wrappers.

## Success Criteria
- No user-visible hangs; cancellations auto-degrade to alternates.
- Dispatcher logs show attempt chains with outcomes; circuit-breakers reduce thrash.
- server.py reduced to a thin orchestrator; modules isolated and testable.
- Kimi flows match Moonshot docs patterns; GLM uses native SDK for robust features.

