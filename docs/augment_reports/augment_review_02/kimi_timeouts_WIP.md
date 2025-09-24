# Kimi multi-file wrapper timeout investigation — WIP note (Phase D)

Summary: After aligning timeout precedence and adding client-abort classification, Kimi multi-file chat succeeds in some runs but still shows intermittent early cancellation (client connection close) at ~3–7s. Server timeouts are not the cause.

## Environment alignment applied
- EXAI_WS_CALL_TIMEOUT=180 (was 90)
- EXAI_SHIM_RPC_TIMEOUT=150 (was 180)
- KIMI_MF_CHAT_TIMEOUT_SECS=50 (≤ FALLBACK_ATTEMPT_TIMEOUT_SECS=60)

Rationale: Ensure precedence KIMI_MF_CHAT_TIMEOUT_SECS ≤ FALLBACK_ATTEMPT_TIMEOUT_SECS ≤ EXAI_WS_CALL_TIMEOUT; reduce premature client aborts.

## Code adjustment (server)
- Added client abort classification around CancelledError in server tool-exec path.
- Emits mcp_activity event with `event="client_abort_suspected"` when elapsed < EX_CLIENT_ABORT_THRESHOLD_SECS (default 10s).

## Evidence (selected patterns from activity log)
- Successful Kimi MF run: upload (200), chat (200), RESPONSE_DEBUG normalized_result_len=1, file_ids present.
- Cancel pattern: TOOL_CANCELLED ~3–5s after file upload; websockets "connection closed" shortly after; no server TIMEOUT.

## Current assessment
- Root cause remains client/extension side timeout/abort during expert/long calls; server is healthy and providing progress heartbeats.

## Next steps
1) Add advisory in logs on `client_abort_suspected` with guidance to raise client wrapper timeout to ≥150s.
2) Re-run a controlled MF validation with a medium file set and unpredictable prompt; capture events and elapsed timings.
3) If intermittent cancels persist, add daemon-side adaptive retry for reattach (semantic call_key) to deliver result on reconnect.

## Notes
- No new tools added or removed — no Augment Settings refresh required.
- Server must be restarted after env or code changes before MCP validations (done).



## Update 2025-09-24 11:15

Changes applied and validated:
- EXAI_WS_PROGRESS_INTERVAL_SECS: 5.0 -> 2.0 (more frequent heartbeats)
- EXAI_WS_DISABLE_COALESCE_FOR_TOOLS: added kimi_multi_file_chat
- EX_AI_MANAGER_ROUTE: true -> false (prevented unintended routes to chat)
- Daemon restarted via scripts/ws/run_ws_daemon.py

Validations:
- ws_chat_once.py (glm-4.5-flash): SUCCESS — real model output returned
- ws_exercise_all_tools.py: core tools activity/analyze/codereview/debug/docgen/health OK; agent tools failed (expected, not configured). Connection dropped at end; will re-run after next batch.

Impact:
- The prior problem where many tools were being routed to chat (missing prompt) is resolved.
- Kimi MF cancellation root cause still suspected as client-side abort; server now emits more frequent progress and avoids coalescing on MF.

Next:
- Attempt a focused kimi_multi_file_chat run (small files) and observe for TOOL_CANCELLED vs completion.
- If cancels persist <10s, confirm CLIENT_ABORT lines and propose client timeout bump in follow-up.


## Update 2025-09-24 11:22

- Direct MCP validations (parallel):
  - chat (glm‑4.5‑flash): SUCCESS — returned two colors + minute
  - kimi_chat_with_tools: SUCCESS — returned two animals + time
  - activity log tail confirms:
    - Earlier kimi_multi_file_chat (explicit glm model) completed via fallback path in ~45.6s
    - New kimi_multi_file_chat (model=kimi-k2-0905-preview) → client_abort_suspected at ~1.99s then TOOL_CANCELLED
- Interpretation: MF cancellation is client‑side abort (consistent with prior RCA). Server heartbeats and fallback orchestration are functioning.
- Action: Proceed with client guidance (timeout ≥150s, disable proactive fallback for expert/long MF) and keep server micro‑steps ON during validation.


## Update 2025-09-24 12:53

- Post-fix clean MCP baseline sweep (activity excerpts):
  - MCP_CALL_SUMMARY: chat — COMPLETE, dur≈16.0s, model=glm-4.5-flash
  - MCP_CALL_SUMMARY: activity — COMPLETE, dur≈0.1s, model=glm-4.5-flash
  - RESPONSE_DEBUG entries show normalized_result_len=1; previews present; no server timeout evidence
- Observation: No new client_abort_suspected events recorded in this short window; prior MF cancellations still attributed to client-side aborts.
- Next: proceed with controlled MF validations after client timeout/fallback settings are confirmed in UI.


## Update 2025-09-24 14:33

- WS daemon restarted and confirmed listening on ws://127.0.0.1:8765
- Executed MCP chat (glm-4.5-flash) with strict format prompt; server returned real output
- Activity excerpts:
  - RESPONSE_DEBUG: raw_result_len=1 tool=chat req_id=9e0b788a-35e4-469e-81d1-5746319bdb6d
  - RESPONSE_DEBUG: normalized_result_len=1 tool=chat req_id=9e0b788a-35e4-469e-81d1-5746319bdb6d
  - TOOL_COMPLETED: chat req_id=9e0b788a-35e4-469e-81d1-5746319bdb6d
- Observation: Summary lines present in earlier sessions; current run emitted RESPONSE_DEBUG/TOOL_COMPLETED (sufficient evidence of live activity). No client_abort_suspected observed in this run.
