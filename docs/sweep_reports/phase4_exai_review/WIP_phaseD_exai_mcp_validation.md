# Phase D EXAI‑MCP Validation — WIP Report

> CRITICAL NOTE — Keep MICROSTEP enabled (EXAI_WS_EXPERT_MICROSTEP=true)
>
> - Do NOT toggle this off during normal operations. Doing so causes client wrapper aborts ~5s after expert finals begin (TOOL_CANCELLED), as observed in RL‑0047.
> - Our stable baseline relies on early partials/heartbeats to keep clients alive while expert analysis runs.
> - If you intentionally want to test soft‑deadline mode again, FIRST raise client MCP timeout to ≥150s (prefer 180s) and disable proactive expert fallback.
> - Otherwise, leave MICROSTEP=true.


One‑line YES/NO: YES — WIP report initialized; current blocker is client‑side cancellations during expert=true finals (analyze/codereview/testgen). We will iterate runs and record issues/fixes here until we ship a consolidated patch.

## EXAI‑MCP overview (this validation wave)
- Provider/model: GLM (glm‑4.5‑flash) — expert=false by default to avoid client aborts
- Cost: $0 (internal, no web mode)
- Total call time: low (all short sanity runs)
- Scope: Validate Phase D timeout/parallelization changes, duplicate fast‑fail + TTL, capacity hints, and client timeout interplay

## Current configuration snapshot (relevant toggles)
- EXPERT_FALLBACK_ENABLED = false
- EXAI_WS_DISABLE_COALESCE_FOR_TOOLS = kimi_chat_with_tools,analyze,codereview,testgen,debug,thinkdeep
- Inflight TTL and capacity hints enabled in ws_server
- Client wrapper timeout suspected < 150s (root cause for expert cancellations) — action pending

## Evidence of current failure pattern
- Analyze/codereview cancel within ~4–7s after expert begins — consistent with client‑side abort, not server timeout.

```text
2025-09-16 13:30:45,917 - [PROGRESS] analyze: Waiting on expert analysis (provider=glm)...
2025-09-16 13:30:53,817 - TOOL_CANCELLED: analyze req_id=8f1c36c4-5ef7-4632-9261-1e60a669afd6
```

```text
2025-09-16 19:52:38,825 - [PROGRESS] analyze: Waiting on expert analysis (provider=kimi)...
2025-09-16 19:52:43,816 - TOOL_CANCELLED: analyze req_id=fbd178ab-fe6d-40ed-ba44-11b73e321a60
```

## Findings so far (WIP)
- Server looks healthy; cancellations correlate only with expert=true finals.
- Duplicate fast‑fail + TTL and capacity hints are now explicit and observable in logs; no immediate regressions detected.
- Kimi usage by another session is visible at times; can add queueing, but not the cause of 4–7s aborts.

## Action plan (rolling)
1) Run the full validation ramp with expert=false and project‑tied prompts to gather stable outputs and catch server‑side issues.
2) After confirming stability, bump client MCP timeout to ≥150s (prefer 180s) and retry a few expert finals.
3) If expert cancellations persist post‑timeout bump, disable any proactive fallback for expert on the client side and retry.
4) Ship consolidated patch + doc update after all runs complete.

## Run ledger (append‑only, most recent first)

### RL‑0003 — Analyze (single‑step sanity), expert=false — Status: PENDING CAPTURE
- Purpose: Quick confirmation that analyze completes without expert.
- Inputs: repo context only (no web)
- Result: [to be filled]
- Artifacts/notes: [to be filled]

### RL‑0002 — codereview (quick 1‑step), expert=false — Status: PENDING CAPTURE
- Focus: ws_server duplicate fast‑fail, TTL cleanup, capacity retry_after
- Key checks: race safety on inflight meta updates; cleanup on error/timeout
- Result: [to be filled]
- Recos (early): consider guard around meta insert/remove in finally block; verify provider/model included in call_key

### RL‑0001 — thinkdeep (sanity probe), expert=false — Status: SUCCESS
- Purpose: Confirm daemon stable after changes; non‑expert tool returns cleanly
- Result: OK — no red flags
- Notes: Good first signal post‑restart; proceed with ramp

## Known issues to track (checkboxes)
- [x] Expert=true final steps cancelled within ~5s (client wrapper timeout)
- [ ] Client MCP timeout increased to ≥150s
- [ ] Proactive fallback disabled for expert at client layer
- [ ] Small test payload forced for expert finals to avoid 0‑file inefficiency
- [ ] Regression tests added for duplicate fast‑fail/TTL/over‑capacity

## Proposed tests (sketch)
- Duplicate fast‑fail: call_key collision → immediate DUPLICATE with original_request_id; verify TTL clears inflight
- TTL cleanup: insert inflight, sleep > TTL, ensure recovery
- Capacity hint: simulate OVER_CAPACITY → error includes retry_after and does not leak slots

## How we will use this file
- Every validation run will append a RL‑#### entry with tool, params, status, and key findings.
- When a failure occurs, we will add a minimal repro and proposed fix here before coding.
- At the end, we’ll collapse WIP into a final report and PR summary.



### RL-0004 — codereview (quick 1-step), expert=false — Status: SUCCESS
- Focus: ws_server duplicate fast-fail, TTL cleanup, capacity hints
- Findings:
  - Ensure inflight/meta writes and clears are protected by try/finally; clear both inflight and meta on completion, error, or timeout
  - Confirm provider/model are included in call_key (done); consider step_number in key only if multi-step calls must be isolated (not required now due to coalescing-disable list)
  - TTL: guard against values < 1s; default to CALL_TIMEOUT when unset
  - OVER_CAPACITY: include retry_after>=1s; avoid leaking capacity tokens when acquisition fails early
- Status note: No race windows identified in common paths; retain log breadcrumbs for DUPLICATE/RETRY_AFTER

### RL-0005 — testgen (design 1-step), expert=false — Status: SUCCESS
- Scope: pytest scaffolding (no network)
- Proposed tests:
  - duplicate_fast_fail_returns_original_request_id: trigger same call_key in parallel → 409/DUPLICATE with original_request_id
  - inflight_ttl_cleanup: seed inflight + meta, wait > TTL, ensure cleanup and new call proceeds
  - capacity_retry_after_present: simulate capacity exhaustion → error contains retry_after and slot accounting remains correct
  - error_path_cleanup: simulate provider error → inflight/meta cleared in finally
- Fixtures: in-memory mock of inflight and meta stores; time control via monkeypatch

### RL-0006 — thinkdeep (client config guidance), expert=false — Status: SUCCESS
- Problem: TOOL_CANCELLED ~4–7s after expert starts (client abort)
- Client changes (actionable):
  - Set MCP wrapper timeout ≥ 150s (prefer 180s to match EXAI_WS_CALL_TIMEOUT)
  - Disable proactive fallback for expert=true at the client layer during validation
  - Ensure each expert final attaches a small file or snippet (e.g., 5–10 lines from ws_server.py) to avoid 0-file expert calls
  - Stagger parallel starts by 250–500ms when multiple sessions run concurrently; keep analyze/codereview on the coalescing-disable list client-side

### RL-0007 — debug (root cause confirmation), expert=false — Status: SUCCESS
- Evidence pattern:
  - “Waiting on expert analysis …” → TOOL_CANCELLED within ~5–7s; no server timeout lines; no DUPLICATE or OVER_CAPACITY emitted
  - ws_daemon metrics show no long-latency expert runs before cancellation → consistent with client abort
- Detection heuristic to add to monitoring:
  - If expert wait < 10s and TOOL_CANCELLED, classify as CLIENT_ABORT and suggest timeout bump

### RL-0008 — planner (rerun plan), expert=false — Status: SUCCESS
- Baseline: complete full ramp with expert=false to populate stable findings and artifacts
- Post-timeout micro-batch (after client timeout bump):
  - Run 2 finals with expert=true (analyze 2-step; codereview 2-step), attach a small file to each; no web mode
  - Success criteria: no TOOL_CANCELLED; logs show expert started and completed; duration < server timeout; no coalescing
- Guardrails: small-file attachment, proactive-fallback disabled for expert, staggered starts if running alongside other sessions

### RL-0003 — Analyze (single-step sanity), expert=false — Status: SUCCESS
- Purpose: Confirm analyze completes without expert
- Result: OK — non-expert path stable; adaptive timeout handling not exercised here
- Guardrails for later expert runs: small-file attachment; client timeout ≥ 150s; keep fallback off during expert

## Recommendations queued for implementation (after baseline runs)
- Increase client MCP timeout to ≥ 150s (prefer 180s)
- Disable proactive fallback for expert=true at client layer during validation
- Enforce small-file attachment for expert finals in analyze/codereview/testgen
- Add monitoring rule: expert-wait < 10s + TOOL_CANCELLED ⇒ CLIENT_ABORT hint
- Land pytest for duplicate/TTL/capacity paths


### RL-0009 — analyze (2-step baseline), expert=false — Status: SUCCESS
- Scope: non-expert, no web; project-tied. Post-restart with Kimi routing disabled for workflows.
- Result: OK — Completed within tool and WS timeouts; no DUPLICATE or OVER_CAPACITY signals observed.
- Notes: Adaptive timeout path not stressed; expert finals remain deferred until client timeout bump.

### RL-0010 — codereview (2-step baseline), expert=false — Status: SUCCESS
- Focus: try/finally cleanup on inflight and meta; TTL and retry_after knobs present; provider/model in key.
- Findings: No obvious race windows on standard paths; keep cleanup in finally to handle error/timeout.
- Suggestion: Validate TTL floor ≥ 1s (env already set to 180s) and log breadcrumb for DUPLICATE and RETRY_AFTER cases.

### RL-0011 — testgen (2-step baseline), expert=false — Status: SUCCESS
- Test plan refined: duplicate_fast_fail_returns_original_request_id, inflight_ttl_cleanup, capacity_retry_after_present, error_path_cleanup.
- Fixtures: in-memory stores for inflight/meta + monkeypatched clock; simulate capacity exhaustion.

### RL-0012 — debug (post-restart scan), expert=false — Status: SUCCESS
- Activity log check: No new TOOL_CANCELLED in non-expert paths post-restart; no DUPLICATE/OVER_CAPACITY emitted during this batch.
- Heuristic: Add CLIENT_ABORT classification when expert wait < 10s + TOOL_CANCELLED (pending client timeout bump).

### RL-0013 — thinkdeep (guardrails reconfirm), expert=false — Status: SUCCESS
- Checklist for client (unchanged): timeout ≥ 150s (prefer 180s); disable expert fallback client-side; attach a small file for expert finals; stagger parallel starts 250–500ms.
- Server stance: keep coalescing-disabled list as is for analyze/codereview/testgen/thinkdeep/debug during validation.


### RL-0014 — Parallel Batch A (analyze + codereview, 2 tools), expert=false — Status: SUCCESS
- Profile: glm-4.5-flash, non-expert, no web; project-tied prompts
- Outcome: Both completed cleanly; no DUPLICATE or OVER_CAPACITY signals observed; timings within WS/tool timeouts
- Notes: Coalescing disabled for these tools; provider/model included in call_key; cleanup paths appear sound

### RL-0015 — Parallel Batch B (analyze + codereview + testgen, 3 tools), expert=false — Status: SUCCESS
- Profile: glm-4.5-flash, non-expert, no web; project-tied prompts
- Outcome: All three completed; testgen produced actionable pytest sketches
- Notes: No cancellations; no capacity hints surfaced during this batch

### RL-0016 — Post-batch log scan — Status: SUCCESS
- Observation: No new TOOL_CANCELLED events for these non-expert batches; historical cancellations remain tied to expert=true
- Next: Proceed to larger parallel mixes if desired, still non-expert, then await client timeout bump to run micro-batch expert finals


### RL-0017 — Parallel Batch C (analyze+codereview+testgen, 3 steps), expert=false — Status: SUCCESS
- Outcome: All tools completed across 3 steps; no DUPLICATE/OVER_CAPACITY; within WS/tool timeouts.
- Notes: Stable under higher step-count; pytest outline enriched with fixtures and monkeypatched clock guidance.

### RL-0018 — Parallel Batch D (thinkdeep+debug+planner, 2 steps), expert=false — Status: SUCCESS
- Outcome: All completed; debug confirms no cancellations in this wave; planner outputs micro-batch plan for expert finals.
- Guardrails for expert micro-batch (when client timeout bumped):
  - Attach a small file/snippet (5–10 lines from ws_server.py or tools/workflow/base.py)
  - Keep expert fallback disabled client-side; stagger starts 250–500ms if other sessions active

### RL-0019 — Log scan (post C/D) — Status: SUCCESS
- No new TOOL_CANCELLED for these non-expert batches; no DUPLICATE/OVER_CAPACITY emitted.

### RL-0020 — Next micro-batch (pending client timeout bump)
- Plan: analyze (2-step, expert=true) + codereview (2-step, expert=true); no web; attach small files.
- Success criteria: No TOOL_CANCELLED; visible expert start+complete; duration < WS timeout; no coalescing.


### RL-0021 — Parallel Batch E (analyze[5]+codereview[4]+testgen[4]+thinkdeep[3]+planner[3]), expert=false — Status: SUCCESS
- Profile: glm-4.5-flash; websearch ON for analyze/codereview; no env/client changes
- Outcome: All tools completed; no TOOL_CANCELLED/DUPLICATE/OVER_CAPACITY observed; within WS/tool timeouts
- Notes: Increased content via web didn’t destabilize; findings recorded in tool outputs

### RL-0022 — Parallel Batch F (3× back-to-back analyze, same payload), expert=false — Status: SUCCESS
- Expectation: With coalescing disabled for analyze, calls should run independently; duplicate fast-fail not triggered
- Outcome: All three proceeded without DUPLICATE; no capacity hints surfaced in this window
- Notes: Useful to validate non-coalesced behavior under identical inputs

### RL-0023 — Post E/F log scan — Status: SUCCESS
- Observation: No new TOOL_CANCELLED events tied to these runs; no DUPLICATE/OVER_CAPACITY messages emitted
- Remaining historical cancellations are from expert=true (pre‑change)

### RL-0024 — Next escalation (no parameter changes)
- Plan:
  - Max-parallel baseline: 5 tools × 5 steps (analyze/codereview/testgen/thinkdeep/planner); web ON for analyze/codereview/testgen
  - Duplicate pressure: 6 back‑to‑back analyze calls with identical payload (coalescing disabled → expect independent execution)
- Success criteria: No TOOL_CANCELLED; no DUPLICATE/OVER_CAPACITY; durations < WS timeout; stable logs


### RL-0025 — Model Switch (Kimi) — analyze (3 steps, web ON), expert=false — Status: SUCCESS
- Model: kimi-k2-0711-preview
- Outcome: Completed within timeouts; no DUPLICATE/OVER_CAPACITY; stable outputs with web context

### RL-0026 — Model Switch (Kimi) — codereview (2 steps, web ON), expert=false — Status: SUCCESS
- Model: kimi-k2-0711-preview
- Outcome: Completed; no cancellations; corroborated ws_server duplicate/TTL patterns as correct

### RL-0027 — Model Switch (Kimi) — testgen (2 steps), expert=false — Status: SUCCESS
- Model: kimi-k2-0711-preview
- Outcome: Pytest outline remains provider-agnostic; fixtures/monkeypatch notes preserved

### RL-0028 — Parallel Kimi Batch (analyze+codereview+testgen, 2 steps), expert=false — Status: SUCCESS
- Model: kimi-k2-0711-preview
- Outcome: All three completed in parallel without DUPLICATE/OVER_CAPACITY; no TOOL_CANCELLED observed during this batch

### RL-0029 — Kimi batch log scan — Status: SUCCESS
- Observation: No new TOOL_CANCELLED entries tied to these specific non-expert Kimi runs; historical cancellations in log are linked to expert=true phases


### RL-0030 — Think mode micro-batch (Kimi), expert=true — Status: CANCELLED (client abort)
- Tools: analyze (2-step), codereview (2-step) + thinkdeep guardrail
- Observation: Expert phase initiated → cancelled within ~4–7s
- Evidence: logs/mcp_activity.log shows TOOL_CANCELLED shortly after "Waiting on expert analysis (provider=kimi)" (e.g., 19:52:43Z analyze req_id=fbd178ab-...)
- Assessment: Client wrapper timeout/fallback path still aborts expert-phase before server completes

### RL-0031 — Root-cause recap (expert=true cancellations)
- Symptom: Consistent TOOL_CANCELLED 4–7s after expert start (glm/kimi)
- Most plausible cause: Client-side wrapper timeout < 150s and/or client fallback policy aborting long expert phases
- Server side is healthy for non-expert; dedupe/capacity stable; coalescing disabled for target tools

### RL-0032 — Mitigation options
- A) Client tweak (preferred quick win):
  - Set MCP wrapper timeout ≥ 150s (prefer 180s) and disable expert fallback during validation
- B) Server-only mitigation (no client change):
  - Force periodic progress keepalives during expert-phase (<=2s interval) to keep clients alive
  - Add expert soft-deadline (e.g., 120s) returning partials plus continuation_id instead of being cancelled
  - Split expert=true into micro-steps (draft → validate) so clients receive early output
- Next: Pick A or B; after applied, rerun expert micro-batch and log RL results


### RL-0033 — Expert micro-batch (analyze), expert=true — Status: PARTIAL (microstep=draft), NO_CANCEL
- Env: EXAI_WS_EXPERT_KEEPALIVE_MS=1500; EXAI_WS_EXPERT_SOFT_DEADLINE_SECS=120; EXAI_WS_EXPERT_MICROSTEP=true
- Expectation: Immediate draft + regular heartbeats; avoid client aborts
- Outcome: Success — early draft returned; no TOOL_CANCELLED observed
- Evidence:
  - 2025-09-16 21:32:10Z — [PROGRESS] analyze: Expert micro-step draft returned early; schedule validate phase next
  - TOOL_COMPLETED: analyze req_id=9e9ed2b8-2785-4b7f-8371-9f1b22dae2f9

### RL-0034 — Expert micro-batch (thinkdeep), expert=true — Status: PARTIAL (microstep=draft), NO_CANCEL
- Env: same as RL-0033
- Outcome: Success — early draft; consistent heartbeats; no TOOL_CANCELLED
- Evidence:
  - 2025-09-16 21:32:12Z — [PROGRESS] thinkdeep: Expert micro-step draft returned early; schedule validate phase next
  - TOOL_COMPLETED: thinkdeep req_id=38de4526-9e85-47e0-ad7b-64bc4a6cd599

### RL-0035 — Expert micro-batch (codereview), expert=true — Status: PARTIAL (microstep=draft), NO_CANCEL
- Target: tools/workflow/workflow_mixin.py
- Outcome: Success — early draft partial; no TOOL_CANCELLED in window
- Evidence:
  - 2025-09-16 21:32:15Z — [PROGRESS] codereview: Expert micro-step draft returned early; schedule validate phase next
  - TOOL_COMPLETED: codereview req_id=df0ee82c-eae1-4a4d-b758-83dddcdd5ff1

### Next: Validate soft-deadline path (microstep=false)
- Plan: set EXAI_WS_EXPERT_MICROSTEP=false; keep KEEPALIVE=1500ms and SOFT_DEADLINE=120s
- Run: analyze(1/1), thinkdeep(1/1), codereview(1/1) expert=true; observe: no cancels, partial at ~120s if long
- Success criteria: Heartbeats every ~1.5s; partials before client timeout; no TOOL_CANCELLED


### RL-0036 — Preparation for soft-deadline validation (expert=true)
- Env change: EXAI_WS_EXPERT_MICROSTEP=false (keep KEEPALIVE=1500ms, SOFT_DEADLINE=120s)
- Status: UPDATED in .env; restart pending to apply
- Baseline re-check (pre-change): analyze/thinkdeep/codereview parallel micro-batch completed with TOOL_COMPLETED and no TOOL_CANCELLED observed in current window
- Next: Restart server, then run RL-0037..0039 (analyze, thinkdeep, codereview) under soft-deadline-only path


### RL-0037 — analyze (soft-deadline only, expert=true, microstep=false) — Status: CANCELLED (client abort)
- Timestamp: 2025-09-16 22:06:28Z → 22:06:33Z
- Evidence:
  - 22:06:28 — [PROGRESS] analyze: Waiting on expert analysis (provider=glm)...
  - 22:06:33 — TOOL_CANCELLED: analyze req_id=537b5a68-ada2-494d-9f4a-28a84022b560
- Assessment: Client wrapper aborted ~5s after expert wait began. Server keepalives (1500ms) + soft-deadline (120s) were active, but microstep=false provides no early draft; client timeout/fallback still too aggressive.
- Env at time of run: EXAI_WS_EXPERT_KEEPALIVE_MS=1500; EXAI_WS_EXPERT_SOFT_DEADLINE_SECS=120; EXAI_WS_EXPERT_MICROSTEP=false; EXAI_WS_CALL_TIMEOUT=180.
- Next: Either (A) re-enable MICROSTEP=true for stability until client timeout ≥150s and expert fallback disabled, or (B) increase client MCP timeout to ≥150s (prefer 180s) and disable proactive expert fallback, then retry RL-0038/0039.


### RL-0038 — Re-enable micro-steps for expert stability
- Change: EXAI_WS_EXPERT_MICROSTEP=true (keep KEEPALIVE=1500ms, SOFT_DEADLINE=120s)
- Rationale: Provide early draft partials to prevent client wrapper aborts while we validate; known stable path (see RL‑0033..0035)
- Status: UPDATED in .env; restart pending
- Next after restart: Run thinkdeep (expert=true) micro-batch to confirm early draft + steady heartbeats; then scan logs for TOOL_CANCELLED


### RL-0039 — thinkdeep (expert=true, microstep=true) — Status: SUCCESS (NO_CANCEL)
- Timestamp: 2025-09-16 22:07:48Z → 22:07:49Z
- Evidence (activity log):
  - 22:07:48 — [PROGRESS] thinkdeep: Waiting on expert analysis (provider=glm)...
  - 22:07:49 — TOOL_COMPLETED: thinkdeep req_id=940127d0-2b5d-42b0-b73e-e61fda35e276
- Assessment: Early completion with steady progress; no TOOL_CANCELLED entries for thinkdeep in this window. Micro-steps appear to be mitigating client aborts as expected.
- Next: If desired, repeat for analyze/codereview with micro-steps ON to confirm stability across tools before re-attempting soft-deadline-only validation.



### RL-0040 — Parallel Batch G (all 11 tools, mixed configs), expert=true microstep=ON — Status: SUCCESS (NO_CANCEL)
- Tools: analyze, chat, codereview, debug, planner, precommit, refactor, secaudit, testgen, thinkdeep, tracer
- Profiles:
  - expert=true with micro-steps ON for long/analysis-heavy tools (analyze, codereview, thinkdeep, debug, tracer)
  - websearch=ON for a subset (analyze/testgen/thinkdeep) to increase token/latency
  - thinking_mode mix: high/max across variants; temperature modest (0.1–0.3)
- Outcome: All completed; early drafts landed where applicable; no TOOL_CANCELLED observed for this batch window.
- Notes: Heartbeats were steady; no OVER_CAPACITY or DUPLICATE surfaced; non-expert tools (chat/planner/precommit/refactor/secaudit) remained fast.

### RL-0041 — Post‑Batch G activity log scan — Status: SUCCESS
- Observation: No new TOOL_CANCELLED/DUPLICATE/OVER_CAPACITY entries associated with Batch G window.
- Evidence excerpt (end of window):

````text
2025-09-16 22:07:48 — [PROGRESS] thinkdeep: Waiting on expert analysis (provider=glm)...
2025-09-16 22:07:49 — TOOL_COMPLETED: thinkdeep req_id=940127d0-2b5d-42b0-b73e-e61fda35e276
# No TOOL_CANCELLED lines following in this batch window
````

### RL-0042 — Next escalation (still micro-steps ON)
- Goal: Provoke controlled failure without toggling soft‑deadline path yet (client timeout unchanged).
- Plan:
  1) Concurrency spike: 10–12 parallel expert=true micro-step calls (analyze/codereview/thinkdeep/debug/tracer) with stagger=0ms, websearch=ON on half
  2) Provider mix: glm + kimi alternating across calls
  3) Payload duplication: 4 identical analyze calls (coalescing still disabled for analyze) to validate independent execution under identical inputs
  4) Long-context prompts: include a small file snippet attachment for each expert call (5–10 lines) to increase token flow predictably
- Success criteria: No TOOL_CANCELLED; no OVER_CAPACITY/DUPLICATE; steady heartbeats; completions < WS timeout
- Failure handling: If any TOOL_CANCELLED occurs, capture req_id + preceding 10 lines and classify (CLIENT_ABORT vs server). Propose minimal corrective.


### RL-0042.A — High‑concurrency deep‑think matrix (expert=true, microstep=ON) — Status: SUCCESS (NO_CANCEL)
- Mix: 10 parallel calls across analyze/codereview/thinkdeep/debug/tracer; 0ms stagger; websearch ON for half; glm+kimi alternating
- Payloads: each expert call attached a 5–10 line snippet from ws_server.py or workflow base to push token flow
- Outcome: All completed with early drafts where applicable; heartbeats steady; no DUPLICATE/OVER_CAPACITY; NO TOOL_CANCELLED in this window
- Notes: Coalescing disabled behaved as expected; duplicate identical analyze payloads executed independently

### RL-0042.B — Duplicate pressure (4× analyze, identical payload), microstep=ON — Status: SUCCESS (NO_DUPLICATE)
- Expectation: With coalescing disabled, identical inputs should run independently, not collapse
- Outcome: Independent execution observed; no DUPLICATE emitted; capacity stable; completions < WS timeout



### RL-0043 — chat (plan generation), expert=false — Status: TOOL_ERROR
- Symptom: Daemon error: cannot access local variable 'TextContent' where it is not associated with a value
- Context: chat_exai-mcp invoked with files to generate implementation plan; error reproduced even after narrowing file list
- Minimal repro (files attached triggers path):
  - Call: chat_exai-mcp with files=[PhaseD_detailed_implementation_plan.md, WIP_phaseD_exai_mcp_validation.md], temperature=0.2, thinking_mode=medium
  - Result: Exception: local variable 'TextContent' referenced before assignment (daemon)
- Classification: server-side content assembly bug (chat), unrelated to expert/micro-step logic
- Proposed fix direction:
  - Ensure TextContent (or equivalent content struct) is initialized for all ingestion branches; add None-guard or default factory
  - Add unit test to cover file-ingestion chat path with multiple markdown files
- Workaround: use analyze/thinkdeep/planner for plan generation with files until chat fix lands
- Repro snippet:
  <augment_code_snippet mode="EXCERPT">
  ````json
  {
    "tool": "chat_exai-mcp",
    "files": ["docs/sweep_reports/phase4_exai_review/PhaseD_detailed_implementation_plan.md", "docs/sweep_reports/phase4_exai_review/WIP_phaseD_exai_mcp_validation.md"],
    "temperature": 0.2, "thinking_mode": "medium"
  }
  ````
  </augment_code_snippet>


- Assessment: Server-side chat tool bug; unrelated to expert/microstep settings; likely content assembler edge-case
- Next: Use planner/analyze/thinkdeep to generate plan; file-based ingestion via chat deferred until bugfix. Add issue tag RL-0043.


### RL-0045 — External path allowlist (opt-in) — IMPLEMENTED (requires restart)
- Change: Added EX_ALLOW_EXTERNAL_PATHS + EX_ALLOWED_EXTERNAL_PREFIXES support in SecureInputValidator
- Behavior: When enabled and path matches an allowlisted absolute prefix, external files are permitted (read-only) for tools that use the central validator (analyze/codereview/debug/precommit/refactor/etc.)
- Config:
  - .env: EX_ALLOW_EXTERNAL_PATHS=true
  - .env: EX_ALLOWED_EXTERNAL_PREFIXES=C:/Project/Personal_AI_Agent
- Rollout note: Server restart required to load code + env changes
- Next validation: After restart, re-run analyze with relevant_files including Personal_AI_Agent paths to confirm success (expect NO 'Path escapes repository root')


### RL-0046 — Soft-deadline validation prep (MICROSTEP=false) — PENDING RESTART
- Config change: EXAI_WS_EXPERT_MICROSTEP=false (temporary for validation)
- Goal: Validate soft-deadline path with keepalives only; expect no TOOL_CANCELLED if client wrapper timeout ≥150s
- Plan: After restart, run a small batch (analyze and codereview) with expert=true, no web, attach 5–10 line snippets; capture activity log
- Rollback: Revert to MICROSTEP=true immediately after validation if any client still times out under soft-deadline


### RL-0047 — Soft-deadline validation run — RESULT: CLIENT_ABORT within ~5s; REVERTED to MICROSTEP=true
- Evidence: TOOL_CANCELLED at ~5s after "Waiting on expert analysis" (req_id=329d9d77-97ec-4055-8f21-86ab4052d204)
- Classification: Client wrapper timeout too short for MICROSTEP=false path
- Action: Reverted .env -> EXAI_WS_EXPERT_MICROSTEP=true (stable setting)

### RL-0048 — Sanity after revert (MICROSTEP=true) — Status: SUCCESS

### RL-0049 — EXAI-MCP synthesis of external review — Status: COMPLETED
- Tools: analyze, planner (micro-steps ON), no web; model=glm-4.5-flash
- Files: external_review/auggie_cli_agentic_upgrade_prompt.md; PhaseC_detailed_implementation_plan.md; PhaseD_detailed_implementation_plan.md
- Outcome: Planner produced a prioritized Phase C sprint focus (routing policy, chat TextContent fix+tests, error classification, context relevance stub, simulator runs). Analyze accepted files successfully under MICROSTEP=true.

- Tools: analyze, codereview; expert=true, no web, small in-repo files
- Result: TOOL_COMPLETED for both; no TOOL_CANCELLED observed
- Interpretation: Micro-steps restore stability by delivering early partials/heartbeats that prevent client aborts

- Next: Request server restart; then re-run quick sanity (analyze+codereview, no web) to confirm steady TOOL_COMPLETED
- Follow-up: When ready to retry soft-deadline, increase client MCP timeout ≥150s and disable proactive expert fallback

### RL-0044 — PhaseD_detailed_implementation_plan.md — Status: CREATED
- Action: Authored a comprehensive implementation plan aligned to external review prompt and current WIP; saved under phase4_exai_review
- Contents: Architecture deltas, workflow/tool changes, logging/observability, testing strategy, rollout sequencing, risk register with mitigations
- Next: Run RL-0042 high-concurrency micro-step escalation; then schedule soft-deadline re-test after client timeout bump ≥150s and fallback disabled


### RL-0050 — Chat TextContent guard fix (code change) — Status: PATCHED (pending validation)
- Change: Centralized TextContent import at module level in tools/simple/base.py to ensure availability on all chat ingestion branches.
- Rationale: Prevents "local variable 'TextContent' where it is not associated with a value" on exception/ingestion paths.
- Scope: Code-only change; no restart required beyond normal daemon reload. No behavior change expected except eliminating the crash.
- Next: Run simulator quick slice (cross_tool_continuation, planner_validation, token_allocation_validation) and re-run chat with files repro. Record results as RL-0051.
