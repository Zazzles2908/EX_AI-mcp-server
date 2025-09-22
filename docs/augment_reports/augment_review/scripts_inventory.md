# Scripts Inventory (Current State)

This document inventories every item under scripts/, describes purpose, dependencies, current usage patterns, and duplicate/overlap notes.

Generated: now

## Legend
- Purpose: brief functional summary
- Deps: notable imports/runtime preconditions
- Usage: Active (A) | Duplicate (D) | Legacy/Obsolete (L) | Unknown (U)
- Notes: duplicates/overlaps or consolidation candidates

## Top-level scripts/

- activate_base.ps1 — PowerShell helper to activate base venv. Deps: PowerShell. Usage: A. Notes: keep under scripts/ (platform-specific).
- activate_moonshot.ps1 — PowerShell env for Moonshot/Kimi. Deps: PS env. Usage: A. Notes: keep.
- activate_zhipuai.ps1 — PowerShell env for ZhipuAI. Usage: A. Notes: keep.
- alias_test.py — Quick alias test harness. Deps: none. Usage: U. Notes: candidate for legacy/diagnostics.
- assess_all_tools.py — Exercises registry tools (stdio/WS agnostic). Deps: tools.registry, src. Usage: A. Notes: diagnostics/validation.
- bump_version.py — Version bumper. Deps: packaging/semver maybe. Usage: U. Notes: tools/.
- check_no_legacy_imports.py — CI-style guard for legacy import paths. Deps: repo. Usage: A. Notes: diagnostics/.
- cleanup_phase3.ps1 — PS cleanup helper. Usage: U. Notes: legacy/.
- cleanup_phase3.py — Python cleanup helper. Usage: U. Notes: legacy/.
- clone_from_zen.ps1 — PS clone bootstrap. Usage: U. Notes: legacy/.
- code_quality_checks.ps1 — PS quality checks runner. Usage: A. Notes: validation/.
- code_quality_checks.sh — Bash quality checks runner. Usage: A. Notes: validation/.
- coverage.ps1 — Coverage runner (PS). Usage: U. Notes: validation/.
- coverage.sh — Coverage runner (bash). Usage: U. Notes: validation/.
- demo_tools.py — Demo of tools usage. Deps: tools.registry. Usage: U. Notes: legacy/examples.
- diagnose_mcp.py — Deep diagnostics for MCP startup/import. Deps: server, env, venv. Usage: A. Notes: diagnostics/.
- exai_agentic_audit.py — Agentic audit via server tools. Deps: server.handle_call_tool. Usage: A. Notes: diagnostics/.
- exai_diagnose.py — Light diag: env keys, import server. Usage: A. Notes: diagnostics/.
- exai_end_to_end.ps1 — PS e2e runner. Usage: U. Notes: e2e/.
- mcp_e2e_auggie_smoketest.py — MCP stdio smoke for auggie. Usage: A. Notes: e2e/.
- mcp_e2e_kimi.py — MCP stdio test for multiple Kimi models. Usage: A. Notes: e2e/.
- mcp_e2e_kimi_tools.py — MCP stdio with Kimi tools. Usage: A. Notes: e2e/.
- mcp_e2e_paid_validation.py — Paid-path validation. Usage: U. Notes: e2e/ (guarded).
- mcp_e2e_smoketest.py — MCP stdio generic smoke. Usage: A. Notes: e2e/.
- mcp_server_wrapper.py — Wrapper to launch server robustly. Usage: A. Notes: keep at root of scripts/ (entrypoint).
- mcp_tool_sweep.py — Sweep all tools (stdio/WS). Usage: A. Notes: validation/diagnostics.
- minimal_server.py — Minimal entrypoint for MCP. Usage: A. Notes: keep (entrypoint).
- progress_test.py — Progress stream test. Usage: U. Notes: diagnostics/.
- router_service_diagnostics_smoke.py — RouterService diagnostics. Usage: A. Notes: diagnostics/.
- run_inline_exai_phase1_review.py — Inline review runner. Usage: U. Notes: legacy/.
- run_integration_tests.ps1 — PS test runner. Usage: A. Notes: validation/.
- run_integration_tests.sh — Bash test runner. Usage: A. Notes: validation/.
- run_kimi_glm_audit_v4.py — Kimi/GLM audit runner. Usage: A. Notes: kimi_analysis/.
- run_thinkdeep_web.py — ThinkDeep orchestrated web run. Usage: A. Notes: diagnostics/.
- run_ws_daemon.py — Start WS daemon. Usage: A. Notes: ws/ (copy exists in scripts/ws/).
- run_ws_shim.py — WS shim bridge. Usage: A. Notes: ws/.
- setup_venvs.ps1 — Create venvs. Usage: U. Notes: tools/.
- show_progress_json.py — Show progress events as JSON. Usage: U. Notes: diagnostics/.
- smoke_tools.py — Quick tool smoke. Usage: A. Notes: validation/.
- sync_exai.ps1 — Sync helper. Usage: U. Notes: tools/legacy.
- tmp_registry_probe.py — Temporary probe. Usage: D/L. Notes: likely remove.
- tool_bench.py — Tool benchmarking harness. Usage: U. Notes: validation/.
- validate_exai_ws_kimi_tools.py — WS Kimi tools validator. Usage: A. Notes: validation/.
- validate_quick.py — Quick env/tools/providers check. Usage: A. Notes: DUP of validation/validate_quick.py.
- validate_websearch.py — Web search validation. Usage: A. Notes: DUP of validation/validate_websearch.py.
- ws_chat_analyze_files.py — WS file analysis chat. Usage: U. Notes: ws/.
- ws_chat_once.py — WS chat once. Usage: A. Notes: DUP of ws/ws_chat_once.py.
- ws_chat_review_once.py — WS review chat. Usage: A. Notes: ws/.
- ws_chat_roundtrip.py — WS GLM+Kimi roundtrip. Usage: A. Notes: ws/.
- ws_exercise_all_tools.py — WS exercise all tools. Usage: A. Notes: DUP of validation/ws_exercise_all_tools.py.
- ws_exercise_all_tools_noauth.py — WS exercise without auth. Usage: A. Notes: DUP of validation/ws_exercise_all_tools_noauth.py.
- ws_start.ps1 — PS start WS. Usage: A. Notes: ws/.
- ws_status.py — WS health printer. Usage: A. Notes: DUP of ws/ws_status.py.
- ws_stop.ps1 — PS stop WS. Usage: A. Notes: ws/.

## Subfolders

- diagnostics/ — README only (placeholder). Usage: A. Notes: will host diagnostics scripts.
- e2e/ — mcp_e2e_kimi.py, README. Usage: A. Notes: consolidate all stdio e2e here.
- kimi_analysis/ — run_backend_kimi_analysis.py, run_kimi_glm_audit_v4.py. Usage: A. Notes: keep.
- tools/ — README only (placeholder). Usage: A. Notes: hosts meta-utilities.
- validation/ — validate_quick.py, validate_websearch.py, ws_exercise_all_tools.py, ws_exercise_all_tools_noauth.py. Usage: A. Notes: canonical locations for these.
- ws/ — run_ws_daemon.py, ws_chat_once.py, ws_status.py, README. Usage: A. Notes: canonical WS scripts.

## Duplicates / Overlaps
- ws_chat_once.py ⇄ ws/ws_chat_once.py — duplicate; prefer ws/ version.
- ws_status.py ⇄ ws/ws_status.py — duplicate; prefer ws/ version.
- ws_exercise_all_tools*.py ⇄ validation/ws_exercise_all_tools*.py — duplicate; prefer validation/ versions.
- validate_quick.py ⇄ validation/validate_quick.py — duplicate; prefer validation/ version.
- validate_websearch.py ⇄ validation/validate_websearch.py — duplicate; prefer validation/ version.

## Candidates for Legacy/Removal
- tmp_registry_probe.py, alias_test.py, cleanup_phase3.py/.ps1, clone_from_zen.ps1, demo_tools.py, run_inline_exai_phase1_review.py


