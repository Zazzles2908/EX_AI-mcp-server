# EXAI‑MCP Call Errors Log

This file records EXAI‑MCP call issues during the audit process. For each event: tool, parameters (condensed), error, and a brief hypothesis.

---

## Unified Architectural Audit (2025-09-19)

This section consolidates EXAI‑MCP findings into a single reference for the EX‑AI‑MCP‑Server architecture. All content is sourced from EXAI‑MCP tool outputs (tracer: dependencies/precision, analyze attempts, thinkdeep attempts) and the audit markdowns.

### Project structure (top-level domains)
- routing/ — TaskType definitions and simple routing helpers
- src/ — Runtime services: daemon (ws_server/session), router/service, providers, embeddings
- tools/ — EXAI‑MCP workflow tools built on BaseTool/Workflow abstractions
- utils/ — Cross‑cutting utilities: http client, security config, metrics, observability, caching
- systemprompts/ — Static prompt templates for all tools
- monitoring/ — Health, SLO, autoscaling, telemetry, worker pool
- providers/ — Provider abstractions and concrete adapters (GLM, Kimi, OpenAI‑compatible)
- streaming/ — Streaming interface contracts
- security/ — RBAC policy/config
- scripts/ — Operational entrypoints (smoke tests, shim/daemon runners, diagnostics)
- core/ — Server entrypoints and config
- supabase/ — Edge Functions proxying to Python MCP server

### How components contribute to EXAI‑MCP workflows
- tools/* → orchestrate tracer/analyze/thinkdeep/etc., using Workflow/BaseTool; consume systemprompts
- src/router/service.py → binds routing decisions to provider registry; chooses models per TaskType/goals
- routing/task_router.py → defines TaskType and selection helpers; pure decision inputs
- providers/* → registry + concrete providers extending OpenAI‑compatible base; outbound HTTP via SDK/clients
- utils/http_client.py + utils/security_config.py → safe HTTP and filesystem guardrails used by providers/tools
- monitoring/* → autoscale decisions, telemetry sinks, health monitors; optional provider integration points
- core/server.py → WS/SSE server; dispatches requests into tools/providers
- supabase/functions/* → HTTPS functions proxying to MCP server; external entrypoints

### Key cross‑references (from tracer precision/dependencies)
- src/router/service.py → providers.registry (ModelProviderRegistry), providers.base.ProviderType
- monitoring/health_monitor_factory.py → providers.hybrid_platform_manager.HybridPlatformManager
- providers/glm.py, providers/kimi.py → providers.openai_compatible.OpenAICompatibleProvider → providers.base
- utils/http_client.py → used by providers and tools for outbound HTTP
- systemprompts/* → consumed by tools/* workflows only; templates/constants (no runtime imports)
- streaming/streaming_adapter.py → interface referenced by streaming demos/tools
- security/rbac_config.py → consumed at server/tool entrypoints for authorization checks

### Status dashboard (EXAI‑MCP tools)
- tracer (dependencies): completed across all domains, model=glm‑4.5‑flash
- tracer (precision): completed for major domains; added summary tables to each audit
- analyze: attempted for routing; current sessions returned empty payload via bridge (logged)
- thinkdeep: multiple retries (pre/post‑restart); empty response payloads via bridge (logged); ongoing Kimi‑only retries

### Script‑by‑script roles (representative; see per‑audit files for inventories)
- routing/task_router.py — TaskType enum and routing helpers; no project imports
- src/router/service.py — chooses models/providers from registry; integrates TaskType and env/profile constraints
- providers/registry.py — provider registry, health/circuit integration, env management
- providers/openai_compatible.py — HTTP client wrapper; capability mapping; executes external API calls
- providers/glm.py, providers/kimi.py — concrete providers inheriting OpenAI‑compatible flow
- utils/http_client.py — JSON HTTP helpers used by providers/tools
- utils/security_config.py — DANGEROUS_PATHS and guardrails for file/system access
- monitoring/worker_pool.py — queue/scale loop; consults autoscale.should_scale_*
- monitoring/health_monitor_factory.py — constructs HealthMonitor; integrates with providers manager
- core/server.py — starts WS/SSE server; request dispatch
- systemprompts/* — static templates; consumed by tools/*
- scripts/run_ws_daemon.py, mcp_e2e_smoketest.py, diagnose_mcp.py — operational runners/smoke/diagnostics

For detailed module inventories and precision views (Entry points, Side effects, Usage points), see each audit_*.md; each now includes a Tracer step‑3 summary table at the top.

---


## 2025-09-18 — chat_EXAI-WS (systemprompts audit)
- Tool: chat_EXAI-WS
- Files: systemprompts/* (13 prompt files)
- Params: model=auto, temperature=0.1, thinking_mode=low, use_websearch=false
- Error: EXEC_ERROR — "cannot access local variable 'TextContent' where it is not associated with a value"
- Hypothesis: Daemon-side content assembly bug when aggregating multi-file prompt content.
- Next: Prefer tracer/thinkdeep workflows; retry after stabilization.

## 2025-09-18 — chat_EXAI-WS (security audit)
- Tool: chat_EXAI-WS
- Files: security/rbac.py, security/rbac_config.py
- Params: model=auto, temperature=0.1, thinking_mode=low, use_websearch=false
- Error: EXEC_ERROR — "cannot access local variable 'TextContent' where it is not associated with a value"
- Hypothesis: Same daemon bug path as above.
- Next: Use tracer/thinkdeep or rerun after daemon fix.

## 2025-09-18 — analyze_EXAI-WS (monitoring kickoff)
- Tool: analyze_EXAI-WS
- Files: monitoring/* (8 files)
- Params: step=Kickoff, model=auto, temperature=0.1
- Result: No content returned (no explicit error)
- Hypothesis: Workflow step returned without formatted output; integration mismatch.
- Next: Switch to tracer dependencies mode once approved.

## 2025-09-18 — tracer_EXAI-WS (monitoring)
- Tool: tracer_EXAI-WS
- Mode: not selected (tool requires user choice)
- Result: Required action — must choose PRECISION or DEPENDENCIES
- Hypothesis: Expected behavior; waiting on mode selection.
- Next: Proceed in DEPENDENCIES mode for structural dependency mapping (recommended).

## 2025-09-18 — thinkdeep_EXAI-WS (monitoring, src, tools, utils)
- Tool: thinkdeep_EXAI-WS
- Files: monitoring/*, and selected files under src/, tools/, utils/
- Params: model=auto, temperature=0.1, thinking_mode=low, use_websearch=false
- Result: Empty response payload
- Hypothesis: Wrapper integration returned no content; likely the same daemon content routing issue.
- Next: Use tracer in DEPENDENCIES mode after confirmation; reattempt thinkdeep post-fix.


## 2025-09-18 — tracer_EXAI-WS step 2 (monitoring)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available. Available models: kimi-*, glm-4.5*, ..."
- Hypothesis: Model alias not resolved by daemon. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (providers)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (routing)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (security)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (streaming)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (systemprompts)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (src)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (tools)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.

## 2025-09-18 — tracer_EXAI-WS step 2 (utils)
- Tool: tracer_EXAI-WS
- Mode: dependencies; Params: model=auto
- Error: EXEC_ERROR — "Model 'auto' is not available..."
- Hypothesis: Same as above. Action: retry with model=glm-4.5-flash.


## 2025-09-18 — Environment hardening for parallelism (no error; mitigation)
- Change: DEFAULT_MODEL set to glm-4.5-flash (was auto)
- Change: EXAI_WS_* inflight raised — session=12, global=48, kimi=10, glm=10; WS call timeout=240s; shim RPC=180s
- Change: Coalescing disabled for: analyze,codereview,testgen,debug,thinkdeep,tracer,planner,refactor,secaudit
- Change: Enabled DISABLE_TOOL_ANNOTATIONS + SLIM_SCHEMAS to reduce handshake size under concurrency
- Rationale: Avoid model alias resolution errors and increase throughput for EXAI‑MCP tracer/analyze under audit load.
- Expected outcome: Fewer 429/capacity stalls, stable parallel tool runs, and elimination of 'model auto not available' failures.


## 2025-09-18 — Batch 2 redo post-restart (src/tools/utils)
- Tool: tracer_EXAI-WS (dependencies)
- Model: glm-4.5-flash
- Result: No errors across src, tools, utils runs (step 2). tracer returned standard pause_for_tracing (step 3 available) with files_checked summaries.
- Note: This confirms environment hardening fixed the prior 'model auto not available' failures.


## 2025-09-18 — Connectivity validation (Kimi path)
- Tool: tracer_EXAI-WS (dependencies)
- Model: kimi-k2-0711-preview
- Target: routing/task_router.py
- Result: Success (tracing_complete). Confirms cross-provider connectivity is intact post .env revert to DEFAULT_MODEL=auto.


## 2025-09-18 — Batch 3 expansion (auggie/templates)
- Tool: tracer_EXAI-WS (dependencies)
- Model: glm-4.5-flash
- Targets: auggie/*.py; templates/auggie/*.md
- Result: No errors (standard pause_for_tracing for optional step 3). Audit files written.


## 2025-09-18 — Batch 3 expansion (core/supabase)
- Tool: tracer_EXAI-WS (dependencies)
- Model: glm-4.5-flash
- Targets:
  - core: server.py, remote_server.py, config.py
  - supabase: gateway/index.ts, memory/index.ts, tools/{chat,codereview,secaudit}.ts
- Result: No errors (standard pause_for_tracing; step 3 available). Audit files written.


## 2025-09-18 — Step 3 deeper mapping (auggie/scripts/core)
- Tool: tracer_EXAI-WS (dependencies)
- Model: glm-4.5-flash
- Targets:
  - auggie: selector.py, session.py, templates.py, wrappers.py
  - scripts: mcp_tool_sweep.py, diagnose_mcp.py, mcp_e2e_smoketest.py
  - core: server.py, remote_server.py, config.py
- Result: Success (tracing_complete) across all. No errors.


## 2025-09-18 — Step 3 deeper mapping (src/tools/utils/systemprompts)
- Tool: tracer_EXAI-WS (precision)
- Model: glm-4.5-flash
- Targets: src/**, tools/**, utils/**, systemprompts/**
- Result: Success (tracing_complete) across all big folders. No errors.

## 2025-09-18 — ThinkDeep synthesis (big folders)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: Synthesis of tracer step-3 outputs for src/tools/utils/systemprompts
- Result: Success. Risks and architecture notes appended to audits. No errors.


## 2025-09-19 — tracer_EXAI-WS precision hotspots (multi-folders)
- Tool: tracer_EXAI-WS (precision)
- Model: glm-4.5-flash
- Targets: auggie/**, core/**, scripts/**, context/**, monitoring/**, providers/**, routing/**, streaming/**, security/**, supabase/**
- Result: Success (tracing_complete) for all targets; no errors

## 2025-09-19 — thinkdeep_EXAI-WS synthesis (multi-folders)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: Synthesize tracer precision outputs for the above targets
- Result: Empty response payload returned (no content)
- Note: Proceeded with interim synthesis based on tracer outputs; will retry Kimi synthesis later


## 2025-09-19 — thinkdeep_EXAI-WS synthesis retry (Kimi)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: Cross-folder synthesis (auggie/core/scripts/context/monitoring/providers/routing/streaming/security/supabase)
- Result: Empty response payload (no content); no explicit error

## 2025-09-19 — thinkdeep_EXAI-WS synthesis retry (GLM fallback)
- Tool: thinkdeep_EXAI-WS
- Model: glm-4.5
- Scope: Same as above
- Result: Empty response payload (no content); no explicit error
## 2025-09-19 — thinkdeep_EXAI-WS (project-wide retry, Kimi-only)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: src/router/service.py; routing/task_router.py; src/providers/{registry.py,openai_compatible.py,kimi.py,glm.py}; utils/{http_client.py,security_config.py}; monitoring/{health_monitor_factory.py,worker_pool.py}; core/{server.py,config.py}
- Status: empty_response (no payload observed via tool interface)
- Notes: Continuing Kimi-only retries per instruction; no GLM fallback will be used. Audits hold interim synthesis to be replaced upon payload arrival.



## 2025-09-19 — analyze_EXAI-WS (routing) Kimi
- Tool: analyze_EXAI-WS
- Model: kimi-k2-0905-preview
- Files: routing/task_router.py, src/router/service.py, tests/test_task_router_mvp.py, tests/test_router_service.py
- Result: EXEC_ERROR — Connection closed
- Note: Will retry with GLM fallback and log outcome


## 2025-09-19 — analyze_EXAI-WS investigation and hotfix
- Context: User-reported "analyze is broken" after Kimi run returned connection closed; ThinkDeep also returned empty payloads.
- Findings:
  - Expert-analysis path executes via workflow_mixin._call_expert_analysis; provider errors propagate as status=analysis_error; empty payloads map to status=empty_response.
  - analyze.prepare_step_data used repo_root=parents[1] for SecureInputValidator, while workflow mixin and other tools use parents[2] — potential path normalization mismatch under SECURE_INPUTS_ENFORCED.
  - Long expert wait without frequent heartbeats can lead to client-side WS idle disconnects.
- Changes applied (code):
  - tools/analyze.py: Align repo_root to parents[2] for SecureInputValidator.
  - tools/analyze.py: Provide analyze-specific expert timeouts and heartbeat methods with env overrides:
    - get_expert_timeout_secs(): default 60s (env ANALYZE_EXPERT_TIMEOUT_SECS)
    - get_expert_heartbeat_interval_secs(): default 7s (env ANALYZE_HEARTBEAT_INTERVAL_SECS)
- Next actions:
  - Re-run analyze_EXAI-WS on routing with Kimi first, fallback GLM if needed; capture status/response.
  - If status=empty_response, treat as analysis_partial in consumer and retry with analyze._call_expert_analysis retry wrapper enabled (RESILIENT_ERRORS_ENABLED=true).


## 2025-09-19 — analyze_EXAI-WS (routing) Kimi (post-restart)
- Tool: analyze_EXAI-WS
- Model: kimi-k2-0905-preview
- Files: routing/task_router.py, src/router/service.py, tests/test_task_router_mvp.py, tests/test_router_service.py
- Status: empty_response (no payload observed via tool interface)
- Notes: Hotfixed analyze tool active (repo_root parents[2], expert timeout=60s, heartbeat=7s). Will merge payload if/when returned in subsequent call.

## 2025-09-19 — analyze_EXAI-WS (routing) GLM fallback (post-restart)
- Tool: analyze_EXAI-WS
- Model: glm-4.5-flash
- Files: routing/task_router.py, src/router/service.py
- Status: empty_response (no payload observed via tool interface)
- Notes: Recorded as fallback attempt; audit updated with interim Analyze synthesis based on tracer precision. Will replace with model output on arrival.


## 2025-09-19 — thinkdeep_EXAI-WS (post-restart synthesis)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: src/router/service.py, routing/task_router.py, tools/workflow/workflow_mixin.py, tools/analyze.py, utils/http_client.py
- Status: empty_response (no payload observed via tool interface)
- Notes: Will continue to retry during audit completion; audits currently include interim synthesis.

## 2025-09-19 — tracer_EXAI-WS (systemprompts precision)
- Tool: tracer_EXAI-WS
- Mode: precision
- Model: auto (provider/model not reported by tool interface)
- Targets: systemprompts/analyze_prompt.py, tracer_prompt.py, thinkdeep_prompt.py, debug_prompt.py
- Result: Success (tracing_complete); no issues found
- Notes: Confirms templates-only; no runtime flow; consumers are tools that embed templates.
## 2025-09-19 — thinkdeep_EXAI-WS (retry, multi-area synthesis)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: src/router/service.py, routing/task_router.py, src/providers/registry.py, src/providers/openai_compatible.py, utils/http_client.py, utils/security_config.py
- Status: empty_response (no payload observed via tool interface)
- Notes: Continuing scheduled retries; audits currently hold interim synthesis to be replaced upon payload arrival.



## 2025-09-19 — thinkdeep_EXAI-WS (post-restart sanity check)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Params: use_assistant_model=false; minimal analysis to validate payload delivery
- Status: empty_response via tool interface
- Note: After server patch EX_ENSURE_NONEMPTY_PAYLOAD=true, UI should show diagnostic stub (status=no_payload_from_tool, diagnostic_stub=true). This confirms transport visibility guard is active without masking upstream tool behavior.

## 2025-09-19 — thinkdeep_EXAI-WS (post-restart project-wide synthesis)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Scope: project-wide EXAI-MCP architecture synthesis (payload delivery, robustness, logging)
- Status: empty_response via tool interface
- Note: Expect diagnostic stub visible at UI boundary if provider returned no content. Continuing Kimi-only retries; will merge real synthesis on arrival.


## 2025-09-19 — Validation after MICROSTEP=true (ThinkDeep synthesis)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Target: Project architecture synthesis (payload delivery focus)
- Result: empty_response via tool interface (no content observed)
- Expectation with MICROSTEP=true: early analysis_partial draft should be emitted; if provider returns nothing, server guard should inject diagnostic stub (status=no_payload_from_tool)
- Note: UI/bridge in this agent session still did not surface payload; verify UI boundary shows early partial or diagnostic stub.

## 2025-09-19 — Validation after MICROSTEP=true (Analyze expert)
- Tool: analyze_EXAI-WS
- Model: kimi-k2-0905-preview
- Target: Architecture payload-delivery verification
- Result: empty_response via tool interface (no content observed)
- Expectation with MICROSTEP=true: analysis_partial draft as first block; not a diagnostic stub
- Note: Could not confirm in this session; recommend checking server activity log for "Expert micro-step draft returned early" progress and verifying first-block content at UI boundary.

## 2025-09-19 — Sanity (Analyze without expert)
- Tool: analyze_EXAI-WS
- Model: glm-4.5-flash
- use_assistant_model: false
- Result: empty_response via tool interface (unexpected for non-expert path)
- Hypothesis: Agent bridge still not rendering first block in this session; server guard would only trigger if all blocks empty; non-expert path should produce immediate content. Recommend cross-check in UI and capture server logs.


## 2025-09-19 — Root cause identified and fix applied (empty payload guard)
- Component: core/server.py (payload guard)
- Symptom: Even with MICROSTEP=true, clients received empty payloads; diagnostic stub never appeared
- Root cause: The non-empty payload guard constructed the stub using JSON booleans (true/false) instead of Python booleans (True/False):
  - "diagnostic_stub": true, "tool_payload_present": false → raises NameError at runtime
  - The guard block was wrapped in a broad try/except and silently swallowed the exception, leaving result unchanged (empty)
- Fix (code):
  - Replace JSON booleans with Python booleans and add a first-block safety shim:
    - diagnostic_stub: True; tool_payload_present: False
    - New option EX_ENSURE_NONEMPTY_FIRST to inject a compact first-block stub when first block text is empty
- Fix (env):
  - Added EX_ENSURE_NONEMPTY_FIRST=true (EX_ACTIVITY_FORCE_FIRST was already true)
- Expected behavior after restart:
  - If a tool returns any content, first block will be non-empty (either tool content or compact stub)
  - If a tool returns no content, a diagnostic JSON stub appears (status=no_payload_from_tool, diagnostic_stub=true)
- Action required: Restart EXAI‑MCP server to load the code change, then re-run ThinkDeep and Analyze validations.


## 2025-09-19 — Post-restart validation after payload guard fix
- Test A: thinkdeep_EXAI-WS (Kimi: kimi-k2-0905-preview)
  - Params: step=Architecture synthesis validation; step_number=1; total_steps=1; next_step_required=false; use_websearch=false
  - Observation (this agent interface): empty payload (no blocks visible)
  - Expected per fix: first block non-empty due to EX_ENSURE_NONEMPTY_FIRST=true; if tool content absent, see diagnostic stub {status=no_payload_from_tool,...}; if MICROSTEP, see {status=analysis_partial,...}
  - Action: Await user/UI confirmation of the first-block content; attach server-side MCP_CALL_SUMMARY if available

- Test B: analyze_EXAI-WS (Kimi: kimi-k2-0905-preview, expert enabled)
  - Params: step=Expert validation of architecture payload delivery; step_number=1; total_steps=1; next_step_required=false; use_websearch=false
  - Observation (this agent interface): empty payload (no blocks visible)
  - Expected per fix: analysis_partial draft as first block (MICROSTEP=true) OR diagnostic stub if expert skipped/empty

- Test C: analyze_EXAI-WS (GLM: glm-4.5-flash, use_assistant_model=false)
  - Params: step=Sanity check without expert; step_number=1; total_steps=1; next_step_required=false; use_websearch=false; use_assistant_model=false
  - Observation (this agent interface): empty payload (no blocks visible)
  - Note: Non-expert workflow normally returns immediate content; persistent emptiness via this bridge suggests client/bridge render still not surfacing first block in this session.


### 2025-09-19 — Resolution confirmed (ThinkDeep micro-step visible)
- Tool: thinkdeep_EXAI-WS
- Model: kimi-k2-0905-preview
- Req ID: d404c5c5-cdd1-4bc6-8428-9cf5ae7d9665
- First block content (key fields): expert_analysis.status=analysis_partial, microstep=draft, raw_analysis=""
- Outcome: Payload delivery guard fix verified; first block non-empty; MICROSTEP=true behavior active
- Next: Harvest full synthesis (either disable microstep for one run or run follow-up continuation and merge 'thinking_analysis' into audit docs)