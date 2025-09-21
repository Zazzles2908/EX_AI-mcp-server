# Phase D Detailed Implementation Plan — EXAI‑MCP Server and Auggie CLI

One‑line YES/NO: YES — Proceed with micro‑steps ON for expert stability now; prepare client timeout ≥150s before re‑testing soft‑deadline. This plan reduces complexity, preserves design integrity, and sequences safe rollouts with full validation.

## 1) Objectives and Scope
- Stabilize expert=true flows immediately using expert micro‑steps + steady heartbeats
- Plan a safe path to validate soft‑deadline‑only after client timeout bump (≥150s, prefer 180s) and expert fallback disabled client‑side
- Consolidate logging/observability and add failure classification (CLIENT_ABORT vs SERVER)
- Improve duplicate fast‑fail/TTL/capacity hints and ensure no slot leakage under stress
- Provide end‑to‑end testing strategy (unit + simulator) and rollout sequencing

## 2) Architecture Deltas (Target State)
1. Expert execution modes
   - Default: micro‑steps ON for long/analysis tools (analyze, codereview, thinkdeep, debug, tracer)
   - Alternate: soft‑deadline‑only path validated later (keepalive ~1.5s, soft‑deadline ~120s, client timeout ≥150s)
2. Heartbeats and soft‑deadline
   - Keepalive cadence: EXAI_WS_EXPERT_KEEPALIVE_MS=1500
   - Soft‑deadline partials: EXAI_WS_EXPERT_SOFT_DEADLINE_SECS=120 (return partial + continuation_id)
3. Client interplay (required for soft‑deadline validation)
   - MCP wrapper timeout ≥150s (prefer 180s)
   - Disable proactive fallback for expert during validation windows
   - Attach a small file/snippet (5–10 lines) to each expert final to avoid 0‑file expert inefficiency
4. Duplicate/coalescing and capacity
   - Keep coalescing disabled for analyze/codereview/testgen/thinkdeep/debug during Phase D
   - Duplicate fast‑fail: include original_request_id; ensure inflight/meta cleared on all paths (success/error/timeout)
   - Capacity: emit retry_after≥1s; never leak tokens on early exits
5. Provider routing
   - GLM primary, Kimi used selectively; preserve model in call_key and logs
   - Stagger starts 250–500ms when multi‑session concurrency is high

## 3) Tool/Workflow Changes
- Standardize expert micro‑steps
  - For analyze/codereview/thinkdeep/debug/tracer: draft micro‑step returns early partial; validate phase optional
  - Guardrails: attach small snippet for expert finals; maintain provider/model in call_key; keep coalescing‑disabled list intact
- Workflow mixin/base adjustments (confirm/current per WIP)
  - try/finally for inflight/meta clear; TTL floor ≥1s; default TTL to CALL_TIMEOUT when unset
  - Add breadcrumbs: DUPLICATE, RETRY_AFTER (with retry_after), CLIENT_ABORT classification when expert wait <10s then cancelled

## 4) Logging and Observability
- Activity log
  - Ensure events for TOOL_CALL, PROGRESS (heartbeats), TOOL_COMPLETED, TOOL_CANCELLED, DUPLICATE, OVER_CAPACITY
  - Add expert‑phase markers: “Expert micro‑step draft returned early”, “Waiting on expert analysis (provider=…)”
- Error classification
  - If expert wait <10s and TOOL_CANCELLED → classify as CLIENT_ABORT (likely client timeout/fallback)
  - Else correlate with provider or server timeouts
- Correlation
  - Preserve req_id across duplicate fast‑fail: include original_request_id in DUPLICATE response
  - Include provider/model and expert_mode (microstep/soft‑deadline) in breadcrumbs

## 5) Testing Strategy
A) Unit tests (pytest)
- duplicate_fast_fail_returns_original_request_id
- inflight_ttl_cleanup (seed inflight/meta, wait > TTL, verify recovery)
- capacity_retry_after_present (simulate capacity exhaustion; assert no leaks)
- error_path_cleanup (provider error → inflight/meta cleared in finally)

B) Simulator tests (recommended quick set)
- cross_tool_continuation (chat/thinkdeep/codereview/analyze/debug threading)
- conversation_chain_validation
- planner_validation + token_allocation_validation
- codereview_validation + refactor_validation
- Optional: run integration with local models via Ollama (safe/free)

C) Phase D validation ramp (from WIP)
- RL‑0042 high‑concurrency micro‑step escalation (10–12 parallel expert=true micro‑step calls; provider mix; file snippets)
- After client timeout bump: re‑test soft‑deadline‑only with analyze/codereview (2‑step), no web, snippet attached

## 6) Rollout / Restart Sequencing
1) Baseline (already stable)
- Keep MICROSTEP=true for long tools; KEEPALIVE=1500ms; SOFT_DEADLINE=120s; CALL_TIMEOUT=180s
- Confirm parallel batches (non‑expert + expert micro‑steps) show NO_CANCEL, no DUPLICATE/OVER_CAPACITY

2) Client prep (required before soft‑deadline re‑test)
- Increase MCP wrapper timeout ≥150s (prefer 180s)
- Disable proactive expert fallback
- Enforce small snippet attachment for expert finals

3) Soft‑deadline re‑test (small controlled batch)
- analyze(2‑step, expert=true, microstep=false) and codereview(2‑step, expert=true, microstep=false)
- Success: steady heartbeats, partial at soft‑deadline if long, NO TOOL_CANCELLED

4) Consolidation
- If stable, consider narrowing coalescing‑disabled list case‑by‑case with tests
- Land unit tests + simulator tests; update docs

## 7) Risk Register and Mitigations
- CLIENT_ABORT during expert finals (likely)
  - Mitigate: client timeout ≥150s, disable fallback, micro‑steps ON until verified
- Provider rate‑limit/capacity exhaust
  - Mitigate: retry_after≥1s, stagger starts, avoid slot leakage, observable breadcrumbs
- Duplicate mishandling
  - Mitigate: explicit DUPLICATE with original_request_id; clear inflight/meta on all paths; tests
- Capacity token leakage on early error
  - Mitigate: acquisition guarded + finally cleanup; tests simulate error paths
- WS instability during high concurrency
  - Mitigate: consistent heartbeats; structured PROGRESS; stagger starts; monitor logs
- Log growth/noise
  - Mitigate: breadcrumb sampling if needed; keep essential fields; log rotation (already configured)

## 8) Immediate Next Steps (Actionable)
- Execute RL‑0042 high‑concurrency micro‑step escalation (no restart required)
- Prepare client changes (timeout/fallback) to enable soft‑deadline re‑test
- Implement/commit pytest unit tests listed above
- Run simulator quick suite; fix regressions if found; re‑run
- Document CLIENT_ABORT heuristic and soft‑deadline validation criteria in WIP

## 9) Done Definition for Phase D
- All micro‑step expert batches pass without TOOL_CANCELLED under high concurrency
- Soft‑deadline‑only flows verified post client timeout bump with NO_CANCEL
- Unit + simulator tests added and passing locally
- WIP report closed out with final summary; PR includes plan, tests, and doc updates


## 10.1) Kickoff — Starting now
- Policy reminder: Keep MICROSTEP=true as the default; do not toggle during normal ops. Soft‑deadline re‑tests only after client timeout ≥150s and fallback disabled.
- Today’s immediate actions:
  1) Add unit tests supporting recent changes (in progress; allowlist test added under tests/test_secure_input_validator.py)
  2) Implement chat file‑ingestion fix (TextContent) and add a dedicated unit test
  3) Run simulator quick suite (cross_tool_continuation, planner_validation, token_allocation_validation)
  4) Execute RL‑0042 high‑concurrency micro‑step escalation and log results in the WIP ledger
- Success criteria: All simulator tests green; RL‑0042 shows no TOOL_CANCELLED; chat file‑ingestion path stable with files attached



## 10) Known Issue — RL-0043: chat_exai-mcp file ingestion (TextContent)
- Symptom: Exception "local variable 'TextContent' where it is not associated with a value" when chat is invoked with files attached
- Repro: files=[PhaseD_detailed_implementation_plan.md, WIP_phaseD_exai_mcp_validation.md], temperature=0.2, thinking_mode=medium
- Classification: server-side content assembly bug; independent of expert/micro-step logic
- Current status: PATCH APPLIED — centralized TextContent import in tools/simple/base.py to ensure availability on all ingestion/error branches; pending validation.
- Validation plan:
  - Add unit test to cover multi-file markdown ingestion for chat
  - Run simulator quick slice including chat with files; confirm no crash and proper content assembly
  - Document outcomes in WIP as RL-0051
- Interim workaround: use analyze/thinkdeep/planner for plan generation with files until validation passes

## 11) Soft-deadline Validation Gate (Prereqs and Steps)
- Prerequisites (client):
  - MCP wrapper timeout ≥150s (prefer 180s)
  - Disable proactive fallback for expert during validation
  - Attach a small 5–10 line snippet to each expert final
- Server settings for this test:
  - EXAI_WS_EXPERT_KEEPALIVE_MS=1500
  - EXAI_WS_EXPERT_SOFT_DEADLINE_SECS=120
  - EXAI_WS_EXPERT_MICROSTEP=false (only for this validation run)
- Steps:
  1. Run analyze(2-step, expert=true) and codereview(2-step, expert=true) with no web, snippet attached
  2. Observe steady heartbeats; expect partial at soft-deadline if long
  3. Verify NO TOOL_CANCELLED; if cancellation <10s after expert wait → classify as CLIENT_ABORT and revisit client timeout/fallback
- Exit criteria: Both complete without cancellation; logs show soft-deadline partials or full completion within server timeout

## 12) Source-of-Truth Notes
- During Phase D, treat this plan and WIP_phaseD_exai_mcp_validation.md as the live sources to drive improvements and code cleanup.
- All validation outcomes (success/fail) must first be recorded in WIP; implementation changes should reference the corresponding RL-####.
