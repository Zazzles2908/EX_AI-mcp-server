# EXAI WebSocket Daemon: Robust Parallelism & Timeouts Strategy (Phase D)

This document captures the finalized approach to make the EXAI–MCP stack robust and powerful under concurrent load without masking hangs. It consolidates investigations, decisions, and the practical steps to configure, implement, and verify the system.

## One‑line summary
- Make call_key unique per request (or disable semantic coalescing per tool) so parallel calls don’t block.
- Align client timeout with server ceilings (150–180s) and keep adaptive expert timeouts.
- Add clear observability (trace_id, heartbeats, CALL SUMMARY) and enforce capacity/backpressure.
- Verify sequential → parallel → chaos with measurable metrics.

## Root causes identified
1) Client/extension cancellations around ~8–10s during expert=true phases (client timeout too short).
2) Daemon semantic de‑duplication treating parallel calls with identical arguments as duplicates, leading to “duplicate call_key timed out after NNNs”.
3) Wrapper/shim logging did not surface call_key/trace_id or de‑dup decisions clearly.

## Final timeout profile (runtime)
- EXAI_WS_CALL_TIMEOUT: 180s (daemon call ceiling)
- EXAI_SHIM_RPC_TIMEOUT: 150s (client→shim)
- WORKFLOW_STEP_TIMEOUT_SECS: 120s (intermediate steps)
- EXPERT_ANALYSIS_TIMEOUT_SECS: 90s (expert budget, +30s buffer, capped under WS−5s)
- EXPERT_HEARTBEAT_INTERVAL_SECS: 5s (progress during expert waits)
- EXAI_WS_PROGRESS_INTERVAL_SECS: 5s (daemon progress cadence)

Rationale: Typical expert runs complete in ~35–60s. These values prevent premature cancellations without masking real hangs.

## Parallelism and idempotency
- Daemon makes a semantic `call_key` from `{name, arguments}`. Identical inputs coalesce.
- For parallel safety now: disable coalescing for analysis tools via env so each call_key is unique.
  - `EXAI_WS_DISABLE_COALESCE_FOR_TOOLS=kimi_chat_with_tools,analyze,codereview,testgen`
- Medium‑term (code change): Keep coalescing by default but fast‑fail true duplicates with HTTP‑style 409 instead of waiting full timeout, and introduce per‑call unique `call_key` at the wrapper.

## Observability & diagnostics
- Continue MCP CALL SUMMARY blocks at completion.
- Emit heartbeats every 5–10s during long expert waits with elapsed and remaining budget.
- Prefer distinct IDs:
  - `trace_id` for correlation across client → shim → daemon → server → provider.
  - `call_key` solely for idempotency/coalescing (opaque).
- Wrapper/shim should log at INFO on call start: tool, trace_id, call_key (hashed), model, timeouts.
- WARN on duplicate rejected (include original request_id).

## Capacity & backpressure (initial)
- Global inflight target: 12–16; per‑tool caps (e.g., analyze=3, codereview=3, testgen=4).
- Provider caps (example): GLM=4, Kimi=6. Tune by provider limits.
- If capacity reached: return 429 with retry_after; wrapper retries with jitter (3 attempts).

## Immediate configuration changes (no code changes)
- Ensure .env values:
  - `EXAI_WS_CALL_TIMEOUT=180`
  - `EXAI_SHIM_RPC_TIMEOUT=150`
  - `WORKFLOW_STEP_TIMEOUT_SECS=120`
  - `EXPERT_ANALYSIS_TIMEOUT_SECS=90`
  - `EXPERT_HEARTBEAT_INTERVAL_SECS=5`
  - `EXAI_WS_PROGRESS_INTERVAL_SECS=5.0`
  - `EXAI_WS_DISABLE_COALESCE_FOR_TOOLS=kimi_chat_with_tools,analyze,codereview,testgen`
- Client/extension timeout: set to 150–180s (UI/extension setting), with optional 240s "Long‑run" toggle.

## Medium‑term code changes (recommended)
- Wrapper:
  - Generate fresh UUIDv4 `call_key` per request; add `trace_id` for correlation.
  - Log start line with tool, model, timeouts, call_key (hashed), trace_id.
- Daemon:
  - Keep semantic coalescing; for exact duplicate `call_key`, reply immediately with 409 Duplicate pointing to the original request_id (do not wait 180s).
  - TTL on inflight keys = `min(EXAI_WS_CALL_TIMEOUT, 2 × P95(tool_duration))`.
- Server:
  - Preserve adaptive timeouts for final expert steps and standard steps.
  - Include trace_id in CALL SUMMARY.

## Verification plan
1) Sequential smoke (now)
   - Run analyze → codereview → testgen with assistant=true, minimal thinking, web off.
   - Expect green completions, MCP CALL SUMMARY blocks, heartbeats, no watchdog errors.
2) Parallel fast profile (post env + client timeout)
   - Launch 3–6 mixed calls with unique call_keys (coalescing disabled in env as above).
   - Expect no dedupe blocks; durations 20–60s for expert runs.
3) Backpressure test
   - Exceed inflight caps: expect 429s and successful jittered retries.
4) Chaos drills
   - Client early‑close, slow provider, WS reconnect. Ensure logs and outcomes are clear.

## Restart checklist
- .env contains values listed in Immediate configuration changes.
- Client timeout set to ≥150s (ideally 180s). Optional Long‑run mode to 240s.
- Restart WS daemon/shim and EXAI–MCP server.
- Run sequential validation; then run parallel validation.

## Notes
- This doc reflects the final Phase D stabilization posture and should be kept alongside the example MCP configs under `docs/architecture/ws_daemon/examples/`.
- For audits, include source URLs when web is enabled; cap web time per call to 15–30s and cache recent fetches (5 min TTL).

