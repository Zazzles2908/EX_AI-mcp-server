# Phase C Detailed Implementation Plan — Auggie CLI Agentic Upgrade (EXAI‑MCP)

One‑line YES/NO: YES — Proceed with Agentic Enhancement (Phase C) guided by the external review. We will land intelligent routing, advanced context management, resilient error handling, and progressive CLI UX — mapped to our current EXAI‑MCP codebase and providers (Kimi/GLM).

## 1) What “Phase C” means for this repo (mapping the external review)
- External “Phase 2: Agentic Enhancement and UX” → Internal Phase C
- Focus areas brought into this codebase:
  1) IntelligentTaskRouter (provider/model/task routing + cost/latency constraints)
  2) AdvancedContextManager (256K‑aware context budgeting + file ingestion unification)
  3) ResilientErrorHandler (categorization: CLIENT_ABORT vs SERVER; retries; fallbacks)
  4) AdaptiveConfiguration (progressive exposure of config via .env + tool args)
  5) UX for Auggie CLI (progressive disclosure, natural language task to tool mapping)
- Keep expert micro‑steps ON for stability; soft‑deadline mode only after client timeout ≥150s.

## 2) Architecture deltas (target state)
1) Task Router
   - Inputs: tool_name, intent (from NL), constraints (cost ceilings, latency SLO), provider availability
   - Decisions: choose provider/model, enable/disable web, set thinking_mode and temperature caps
   - Integration points: tools/registry.py (build‑time), tools/models.py (request‑time metadata)
2) Context Manager
   - Consolidated file ingestion: normalize via SecureInputValidator; consistent TextContent handling across SimpleTool + Workflow tools
   - Token budgeting: enforce MCP_PROMPT_SIZE_LIMIT, prioritize top‑K snippets by semantic relevance (pluggable embeddings later)
3) Error Handler
   - Standardize failure classes: CLIENT_ABORT, PROVIDER_RATE_LIMIT, PROVIDER_ERROR, SERVER_VALIDATION
   - Retry/backoff: jittered backoff for rate limits; no token leakage; detailed breadcrumbs in logs
4) Adaptive Config
   - .env remains authoritative with concise one‑liners; .env.example holds guidance
   - Tool args can override safe subsets (e.g., provider preference) but never bypass security
5) CLI/UX
   - “Natural command → task plan → tool sequence” pipeline (planner → orchestrate_auto)
   - Progressive disclosure: only the essential options by default; advanced flags on demand

## 3) Concrete changes in this repository
- Routing
  - Add a light TaskRoutingPolicy in providers/registry.py that:
    - Preserves explicit model if user provided
    - Otherwise picks: GLM for fast/cheap, Kimi for long/complex; record rationale in metadata
  - Extend tools/shared/base_tool.py to log chosen provider/model + cost tier
- Context
  - Unify TextContent creation: ensure import available on all codepaths (fix the chat ingestion branch)
  - Introduce a small relevance scorer (stub) for file snippets selection with a budget gate
- Errors
  - Standardize raise/return helpers for: CLIENT_ABORT (<10s cancel after expert wait), OVER_CAPACITY with retry_after, DUPLICATE with original_request_id
  - Ensure finally‑cleanup for inflight/meta paths (already in Phase D plan; verify here)
- Config
  - Add doc strings beside critical envs; keep .env minimal; update .env.example with richer notes
- CLI
  - Map common NL intents → initial tool choices (planner → analyze/codereview/refactor/testgen) with a short rationale

## 4) Logging and observability (Phase C level)
- Activity log must include:
  - tool, provider, model, expert_mode, req_id
  - breadcrumbs: ROUTE_DECISION, CLIENT_ABORT, RETRY_AFTER, DUPLICATE
- Server log improvements:
  - One‑line summaries per tool run; sampling kept reasonable; rotation already enabled

## 5) Security posture (no regressions)
- Keep repository‑root containment with optional external prefix allowlist
- Validate images/file limits per provider model; block unknown MIME/oversized payloads
- Preserve read‑only external access; never broaden prefixes without explicit env change

## 6) Testing strategy (Unit + Simulator)
A) Unit tests (pytest)
- routing_policy_selects_expected_provider_under_constraints
- textcontent_always_initialized_in_chat_ingestion
- secure_input_validator_allowlist_ok (ALREADY ADDED)
- client_abort_classification_when_expert_cancelled_quickly
- capacity_retry_after_and_no_slot_leak

B) Simulator tests (quick set)
- planner_validation, token_allocation_validation, codereview_validation, cross_tool_continuation
- Success signal: no TOOL_CANCELLED with expert micro‑steps ON; correct provider/model breadcrumbs present

C) Optional integration
- Local Ollama path for free runs (out of scope to modify; keep documented)

## 7) Rollout plan (safe, incremental)
1) Land fixes that do not affect behavior under micro‑steps (TextContent/chat ingestion, error classification, breadcrumbs)
2) Introduce TaskRoutingPolicy with conservative defaults; log only at first
3) Enable routing decisions to affect provider/model selection for non‑expert tools by default
4) Add small context relevance scorer gated by budget; keep score‑only mode first
5) Promote relevance‑based trimming to enforced mode after simulator validation

## 8) Success criteria (Phase C)
- 0 regressions in cancellation: NO TOOL_CANCELLED under micro‑steps
- Routing breadcrumbs visible with rationale; explicit requests still respected
- Chat file‑ingestion stable with multiple markdown files
- Unit and simulator suites fully green

## 9) Immediate next steps (actionable)
- Implement chat TextContent fix + unit test
- Add routing policy skeleton with logging only (no behavior change) and unit tests
- Add classification helpers and ensure finally‑cleanup paths return consistent metadata
- Run simulator quick suite → iterate on failures → re‑run
- Document RL entries in WIP Phase D when changes touch runtime behavior

## 10) Quality gates to advance beyond Phase C
- All tests pass locally (unit + simulator quick)
- Routing policy shows correct decisions on logged scenarios; no unexpected provider churn
- Context relevance scorer ready for enforcement with budget guard and passes dry‑run checks

## 11) References (source alignment)
- docs/external_review/auggie_cli_agentic_upgrade_prompt.md
  - Phase 2.1/2.2/2.3/2.4 mapped to our Routing, Context, Error, CLI/UX tracks
- docs/sweep_reports/phase4_exai_review/PhaseD_detailed_implementation_plan.md
  - Keep MICROSTEP=true policy; soft‑deadline only with longer client timeouts

---

## Appendix: Implementation checklist (Phase C)
- [ ] Fix chat ingestion TextContent and add test
- [ ] Add TaskRoutingPolicy (logging‑only mode) + tests
- [ ] Add error classification helpers and breadcrumbs + tests
- [ ] Add context relevance scorer stub + budget guard (dry‑run) + tests
- [ ] Run simulator quick suite and stabilize
- [ ] Update docs (.env.example notes; CLI help text for progressive options)

