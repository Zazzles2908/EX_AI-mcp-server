# Scripts Reorganization Proposal

Goal: reduce clutter, de-duplicate, and standardize entrypoints while preserving backward compatibility.

## Proposed subfolder structure
- scripts/ws: WebSocket daemon, status, and WS-only clients
- scripts/validation: smoke tests, validators, tool exercisers, CI-friendly checks
- scripts/diagnostics: environment/server/router diagnostics and audits
- scripts/e2e: stdio MCP end-to-end tests (auggie/MCP clients)
- scripts/tools: meta-utilities (version bump, setup, sync)
- scripts/kimi_analysis: Kimi/GLM coordinated audits
- scripts/legacy: quarantined old/rarely-used items (kept for reference)

## Mapping (keep/move/consolidate/remove)

- Keep at scripts/ (entrypoints & key wrappers)
  - mcp_server_wrapper.py (keep)
  - minimal_server.py (keep)
  - run_ws_shim.py (keep under ws but ALSO provide top-level shim alias if needed)

- Move to scripts/ws
  - run_ws_daemon.py (MOVE) 
  - ws_chat_analyze_files.py (MOVE)
  - ws_chat_once.py (already duplicated; KEEP ws/ version, mark top-level as legacy)
  - ws_chat_review_once.py (MOVE)
  - ws_chat_roundtrip.py (MOVE)
  - ws_start.ps1, ws_stop.ps1 (MOVE)
  - ws_status.py (already duplicated; KEEP ws/ version, mark top-level as legacy)

- Move to scripts/validation
  - assess_all_tools.py (MOVE)
  - mcp_tool_sweep.py (MOVE)
  - smoke_tools.py (MOVE)
  - tool_bench.py (MOVE)
  - validate_exai_ws_kimi_tools.py (MOVE)
  - validate_quick.py (DUP of validation/validate_quick.py)  KEEP validation/ version, mark top-level as legacy
  - validate_websearch.py (DUP of validation/validate_websearch.py)  KEEP validation/ version, mark top-level as legacy
  - ws_exercise_all_tools.py (DUP of validation version)  KEEP validation/ version, mark top-level as legacy
  - ws_exercise_all_tools_noauth.py (DUP)  KEEP validation/ version, mark top-level as legacy

- Move to scripts/diagnostics
  - diagnose_mcp.py (MOVE)
  - exai_diagnose.py (MOVE)
  - router_service_diagnostics_smoke.py (MOVE)
  - exai_agentic_audit.py (MOVE)
  - run_thinkdeep_web.py (MOVE)
  - progress_test.py (MOVE)
  - show_progress_json.py (MOVE)

- Move to scripts/e2e
  - mcp_e2e_auggie_smoketest.py (MOVE)
  - mcp_e2e_kimi.py (MOVE)
  - mcp_e2e_kimi_tools.py (MOVE)
  - mcp_e2e_paid_validation.py (MOVE)
  - mcp_e2e_smoketest.py (MOVE)
  - exai_end_to_end.ps1 (MOVE)

- Move to scripts/tools
  - bump_version.py (MOVE)
  - setup_venvs.ps1 (MOVE)
  - code_quality_checks.ps1 / .sh (MOVE)
  - coverage.ps1 / .sh (MOVE)
  - sync_exai.ps1 (MOVE)

- scripts/kimi_analysis
  - run_backend_kimi_analysis.py (KEEP)
  - run_kimi_glm_audit_v4.py (KEEP)
  - run_kimi_glm_audit_v4.py at root (DUP)  REMOVE or replace with wrapper to kimi_analysis/

- scripts/legacy (quarantine; keep, no wrappers)
  - alias_test.py, cleanup_phase3.py, cleanup_phase3.ps1, clone_from_zen.ps1, demo_tools.py, run_inline_exai_phase1_review.py, tmp_registry_probe.py

## Backward compatibility wrappers
- For each top-level script being moved, create a thin shim at its old path that imports and calls the new location's main() (if __name__ == "__main__"). This allows existing shortcuts/automation to keep working.
- For exact duplicates (top-level vs subfolder), mark the top-level as legacy and add a deprecation header; prefer not to duplicate logic.

## Removal candidates (safe to remove)
- tmp_registry_probe.py (temporary)
- alias_test.py (developer scratch)
- cleanup_phase3.* (old cleanup)
- clone_from_zen.ps1 (bootstrap)
- demo_tools.py (superseded by validation/ and ws/ examples)
- run_inline_exai_phase1_review.py (old workflow)

## Risks & mitigations
- Risk: external scripts refer to old paths. Mitigation: backward-compat wrappers; deprecation headers; one release cycle before deletion.
- Risk: import paths changed. Mitigation: wrappers only affect CLI invocation; internal imports remain unchanged.

## Rollout plan
1) Commit inventory + proposal docs (this file and scripts_inventory.md)
2) Create missing subfolders (already present), add README(s)
3) Implement wrappers for duplicates (top-level -> subfolder) and update run docs
4) Quarantine legacy candidates in scripts/legacy
5) After one cycle, remove legacy files after confirming no references remain

