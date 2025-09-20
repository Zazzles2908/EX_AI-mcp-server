# EXAI‑WS MCP Validation & Coverage Report

Status: NO — Not fully complete; chat path appears OK, ThinkDeep path is inconsistent (often empty payload); Phase A checklist still has open items.

Provider/Model (observed in logs): GLM (glm‑4.5‑flash), Kimi (kimi‑k2‑0905‑preview)
Cost/Time: N/A (local MCP analysis run; cost not observable here). Total call time: not recorded in this session.

---

## Scope
- Audit files reviewed:
  - docs/augment_reports/audit/consolidation_plan.md
  - docs/augment_reports/audit/migration_checklist_phaseA.md
  - docs/augment_reports/audit/no_legacy_imports_blocker.md
  - docs/augment_reports/audit/removal_candidates.md
  - docs/augment_reports/audit/router_unification_plan.md
  - docs/augment_reports/audit/tools_cleanup_plan.md
  - docs/augment_reports/previous_audit/call_errors.md
  - docs/augment_reports/previous_audit/decision_tree_architecture.md
  - docs/augment_reports/previous_audit/duplicate_domains_map.md
- Code paths sampled (evidence from codebase-retrieval):
  - tools/thinkdeep.py (ThinkDeep tool)
  - tools/registry.py (tool registration; thinkdeep present; core visibility)
  - server.py (tool aliasing/routing; ThinkDeep deterministic model selection)
  - config.py (DEFAULT_THINKING_MODE_THINKDEEP; THINK_ROUTING_ENABLED)
  - scripts/run_thinkdeep_web.py (driver script)
  - docs/tools/thinkdeep.md, docs/standard_tools/advanced-usage.md (usage docs)

## Summary of Findings
- Consolidation & routing plans exist and are mostly implemented. However, Phase A checklist has unchecked items:
  - Grep and update legacy imports (providers.* → src.providers.*) — still pending
  - Smoke validations (listmodels, quick GLM/Kimi chat) — pending in checklist
  - Confirm runtime only uses src/providers registry (log check) — pending
- No‑legacy‑imports blocker documented and wired via CI (scripts/check_no_legacy_imports.py; workflow present).
- Removal candidates listed with a Phase‑F branch status indicating many shim files were already removed in that branch; final deletion pending post‑stabilization window.
- Router unification plan is documented; diagnostics flags/instructions added; needs validation logs in this branch/session.

### EXAI‑WS tool functionality snapshot (from call_errors.md and code evidence)
- chat: Previously hit a daemon content assembly bug; later runs appear stable (no current blocker in this session).
- tracer: Stable when using explicit model (glm‑4.5‑flash). “auto” alias caused errors earlier; defaults hardened since.
- analyze: Multiple empty_response cases even after hotfixes; expert timing/heartbeat aligned and guards added, but UI bridge may still not surface first block in some sessions.
- thinkdeep: Historically returned empty payload via tool interface. A guard fix in server.py changed JSON booleans to Python booleans and added EX_ENSURE_NONEMPTY_FIRST=true; post‑restart validation notes still observed empty blocks in some sessions, but a later entry shows ThinkDeep micro‑step visible with status=analysis_partial — indicating intermittent success depending on client/UI bridge.

Conclusion: The backend wiring for ThinkDeep exists and can produce content (at least micro‑steps), but the user‑reported behavior (“does not work at all”) matches the documented intermittent empty‑payload symptom on some bridges/sessions. Treat as not fully resolved until consistent end‑to‑end runs capture non‑empty first blocks in this environment.

## Evidence excerpts
- tools/registry.py maps thinkdeep:
  - TOOL_MAP["thinkdeep"] → ("tools.thinkdeep", "ThinkDeepTool")
  - TOOL_VISIBILITY marks it as "core"; DEFAULT_LEAN_TOOLS includes "thinkdeep"
- server.py Think routing and aliasing:
  - Name‑level aliasing: unknown names containing "think" reroute to thinkdeep (if THINK_ROUTING_ENABLED)
  - Deterministic model selection: if explicit model not set (or override allowed), route thinkdeep to fast expert model (default GLM_FLASH_MODEL=glm‑4.5‑flash)
- config.py:
  - DEFAULT_THINKING_MODE_THINKDEEP defaults to "high"
  - THINK_ROUTING_ENABLED env toggles aliasing/rerouting
- docs/augment_reports/previous_audit/call_errors.md:
  - Multiple “empty_response” entries for thinkdeep and analyze across Kimi and GLM
  - Fix applied in server.py for non‑empty payload guard; micro‑step visibility confirmed once (status=analysis_partial)

## Gaps and risks
1) ThinkDeep consistency gap
   - Symptom: empty responses in some sessions despite guards; one confirmed successful micro‑step afterward.
   - Risks: Client/bridge not rendering first block; server guard exceptions previously swallowed; potential mismatch in tool payload handling.

2) Phase A validation still open
   - Pending: repo‑wide legacy import grep/replace (providers.*), smoke runs, runtime registry confirmation.

3) Router diagnostics
   - Diagnostics flags added in plan; need real logs captured (route_decision & route_diagnostics) in this branch/session to confirm.

## Recommended next actions
- Run three end‑to‑end smoke validations and capture outputs in docs/augment_reports/audit/logs/:
  1) listmodels (ensure src/providers registry is authoritative and both Kimi/GLM providers list expected models)
  2) chat (GLM and Kimi) with unpredictable prompts; save raw outputs
  3) thinkdeep (two runs):
     - Run A: use_assistant_model=false (non‑expert) — expect immediate content
     - Run B: use_assistant_model=true (expert micro‑step) — expect first block non‑empty; if model returns nothing, diagnostic stub
- If any run returns empty first block, capture server logs around payload guard and confirm EX_ENSURE_NONEMPTY_FIRST and MICROSTEP settings.
- Complete Phase A checklist items, then schedule Phase‑F shim deletions per removal_candidates.md.

## Decision
- Project completion: NO (pending Phase A items + inconsistent ThinkDeep end‑to‑end behavior)
- EXAI‑WS chat: Appears OK currently
- EXAI‑WS thinkdeep: Not reliably OK; intermittent; treat as not complete

## Appendix — Files referenced
- tools/thinkdeep.py; tools/registry.py; server.py; config.py; scripts/run_thinkdeep_web.py
- docs/tools/thinkdeep.md; docs/standard_tools/advanced-usage.md
- docs/augment_reports/audit/*.md; docs/augment_reports/previous_audit/*.md

