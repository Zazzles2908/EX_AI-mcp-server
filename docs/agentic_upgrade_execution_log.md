# Agentic Upgrade: Execution Log and Test Outcomes

This log captures each adjustment, the purpose, restart checkpoints, direct MCP test outcomes, and the next planned action. It will be updated iteratively until all tasks are complete.

---

## 2025-09-14 – Phase A kickoff

Purpose:
- Begin aligning the server with the “agentic upgrade” plan: cost-aware routing, secure inputs, lean registry, and compatibility-safe steps.

Changes applied:
- ModelRouter implemented and integrated into SimpleTool model selection (utils/model_router.py, tools/simple/base.py)
- SecureInputValidator added and wired in SimpleTool path validation with env toggle (src/core/validation/secure_input_validator.py)
- ToolHub adapter added to pave way for registry rename (tools/tool_hub.py)
- Consensus tool marked [DEPRECATED] in description (tools/consensus.py)
- Registry gated unstable orchestrators unless ORCHESTRATORS_ENABLED=true (tools/registry.py)
- .env updated to safe defaults:
  - ORCHESTRATORS_ENABLED=false
  - ROUTER_ENABLED=true
  - SECURE_INPUTS_ENFORCED=true
  - UI_PROFILE=compact
  - GLM_FLASH_MODEL=glm-4.5-flash; GLM_QUALITY_MODEL=glm-4.5; KIMI_DEFAULT_MODEL=kimi-k2-0711-preview

Vital run details captured per iteration:
- Restart timestamp (from server log)
- WS host/port and session id used
- Request payload summary (tool name + key args)
- Security enforcement status (SECURE_INPUTS_ENFORCED)
- Router status and selected model (ROUTER_ENABLED, resolved model)
- Files normalization result (relative→absolute, count)
- Outcome status (ok/error + brief message)
- Next action decided


Checkpoint (server restart):
- Prior restart (from logs) at 2025-09-14 10:45:35 showed orchestrator tool load errors (autopilot), which the registry gating is intended to prevent.
- User confirmed a restart after the .env and registry updates.

Direct MCP tests prepared (end-to-end over WS):
- scripts/ws_call_analyze.py – calls analyze Phase 1 with relevant_files=["server.py"] (relative path on purpose) to validate secure path normalization without needing provider calls.
- scripts/ws_call_chat.py – optional chat call exercising router + normalization (provider-dependent; run if keys are configured).

How to run (PowerShell):
- .\.venv\Scripts\python.exe scripts\ws_call_analyze.py
- .\.venv\Scripts\python.exe scripts\ws_call_chat.py  (optional; requires provider keys)

Outcome:
- Analyze Phase 1 expected behavior: accept relative relevant_files and normalize to workspace path with SECURE_INPUTS_ENFORCED=true; return outputs without model/provider use.
- Chat expected behavior: route to glm-4.5-flash by default (ROUTER_ENABLED=true) and accept relative files by normalization.

Status at this checkpoint:
- Scripts added and ready to run. Awaiting/recording run outputs with the restarted server.

Next actions:
1) Verify analyze Phase 1 succeeds via scripts/ws_call_analyze.py and capture result below.
2) If OK, unify SecureInputValidator in workflow mixins and proceed to chunked file reader + ResilientErrorHandler skeleton.
3) If not OK, fix only that surface and re-test before moving on.

---

## Execution Notes (to be appended live)
- 2025-09-14 – Restart detected: 11:51:01.894 (PID=35012); WS=ws://127.0.0.1:8765
  - Env: SECURE_INPUTS_ENFORCED=true; ROUTER_ENABLED=true; ORCHESTRATORS_ENABLED=false; UI_PROFILE=compact
  - Planned call: analyze Phase 1 (no provider)
    - PowerShell: .\.venv\Scripts\python.exe scripts\ws_call_analyze.py
    - Request: step=Kickoff, step_number=1, total_steps=1, next_step_required=false, relevant_files=["server.py"]
  - Expectation:
    - Files normalization: server.py -> C:\\Project\\EX-AI-MCP-Server\\server.py
    - No expert model call; should return tool output
  - Outcome: [pending]
  - Next: If OK, wire chunked reader behind flag for final/expert steps


- 2025-09-14 – Analyze E2E test: [pending]
  - Command: .\.venv\Scripts\python.exe scripts\ws_call_analyze.py
  - Result: …
  - Next: …

- 2025-09-14 – Chat E2E test (optional): [pending]
  - Command: .\.venv\Scripts\python.exe scripts\ws_call_chat.py
  - Result: …
  - Next: …

- 2025-09-14 – Workflow mixin validator unification: [pending]
  - Purpose: ensure all workflow tools normalize relevant_files via centralized validator
  - Test: rerun analyze with relative relevant_files; expect same normalized behavior

- 2025-09-14 – Chunked file reader (skeleton): [pending]
  - Purpose: include key file regions under token constraints
  - Test: tool with large file should gracefully include selected sections only

- 2025-09-14 – ResilientErrorHandler (skeleton): [pending]
  - Purpose: standardize retries/fallbacks and user-facing error clarity
  - Test: simulate a provider throttling scenario (mock) and verify retry/backoff path

---

## Task alignment summary

Active tasks under Phase A:
- [x] ModelRouter utility integrated into SimpleTool
- [x] SecureInputValidator available and wired into SimpleTool
- [x] ToolHub adapter created (non-breaking)
- [x] Consensus tool description deprecation
- 2025-09-14 – Analyze E2E (final step) BEFORE fix: [observed long wait]
  - Time window: ~11:58:06–11:59
  - Request: next_step_required=false (final); relevant_files=["server.py"], large file
  - Behavior:
    - Workflow treated as final step and attempted full embedding; server.py exceeded file token budget
    - Expert analysis initiated; outbound GLM request observed (200 OK eventually)
    - WS kept session alive with pings; appeared as a “hang” on client
  - Outcome: Slow return due to provider call + large file; acceptable for final steps but not for quick smoke tests
  - Mitigation applied:
    - Changed WS test to Phase 1 only (next_step_required=true, use_assistant_model=false)
    - Added optional CHUNKED_READER_ENABLED path for final/expert steps to avoid budget overflows

- 2025-09-14 – Restart detected: 12:03:24.050 (PID=39384); WS=ws://127.0.0.1:8765
  - Env: SECURE_INPUTS_ENFORCED=true; ROUTER_ENABLED=true; ORCHESTRATORS_ENABLED=false; UI_PROFILE=compact
  - Call: analyze Phase 1 (provider disabled)
    - PowerShell: .\.venv\Scripts\python.exe scripts\ws_call_analyze.py
    - Request: step=Kickoff, step_number=1, total_steps=1, next_step_required=true, use_assistant_model=false, relevant_files=["server.py"]
  - Observations:
    - Only referenced file names (“reference_only” file_context), no embedding, no provider call
    - Response included continuation_id=d9a720a1-... and required actions; status pause_for_analysis
    - Metadata model_used=glm-4.5-flash, provider_used=glm (pre-resolved at boundary) but not actually invoked
  - Outcome: OK – fast local response; validator path exercised; routing visible but not executed
  - Next:
    - Optionally enable CHUNKED_READER_ENABLED=true and test a final step on a large file to validate chunked embedding
    - Begin wiring ResilientErrorHandler around provider calls for friendlier timeouts/retries

- 2025-09-14 – Planned final-step analyze (chunked): [pending]
  - Env: CHUNKED_READER_ENABLED=true; SECURE_INPUTS_ENFORCED=true; ROUTER_ENABLED=true
  - Call: analyze final step on server.py
    - PowerShell: .\.venv\Scripts\python.exe scripts\ws_call_analyze_final.py
    - Request: step_number=1, total_steps=1, next_step_required=false, use_assistant_model=true, relevant_files=["server.py"]
  - Expectation:
    - File context: fully_embedded (chunked) with log note “[WORKFLOW_FILES] Used CHUNKED reader”
    - Provider call performed (GLM) and completes without long wait due to reduced payload size
  - Outcome: [pending]

- [x] Orchestrators gated by env to prevent startup errors
- [x] .env defaults adjusted
- [ ] Workflow mixin validator unification
- [ ] Chunked file readers (skeleton)
- [ ] ResilientErrorHandler (skeleton)
- [ ] Docs and tests for router decisions and validation flows

This document will be updated after each restart/test cycle with precise outcomes and the next step taken.


- 2025-09-14 – Provider resilience wrappers added: [GLM, Kimi]
  - Files: src/providers/glm.py (retry + friendly message), src/providers/kimi.py (retry + friendly message)
  - Env knobs: RESILIENT_RETRIES=2, RESILIENT_BACKOFF_SECS=1.5 (default)
  - Behavior: transient network/429 errors will retry with exponential backoff; persistent failures surface concise messages
  - Next: Restart and run final-step analyze (chunked) to validate end-to-end
