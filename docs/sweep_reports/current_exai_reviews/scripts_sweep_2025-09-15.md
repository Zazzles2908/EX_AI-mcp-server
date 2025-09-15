# Scripts Sweep Report (EXAI MCP generated)

## Summary
This report classifies scripts and points to EXAI MCP-first workflows so day-to-day validation and QA feel simple and consistent. Where scripts add little beyond EXAI MCP, we mark them for deprecation with a banner and a short sunset note.

## Classification Table
Script | Purpose | Status | Replacement / EXAI route | Notes/Banner
---|---|---|---|---
scripts/mcp_server_wrapper.py | Stable server bootstrap for MCP clients (VS Code/Auggie) | Canonical | Keep; default entrypoint | Required for your default WS shim setup
scripts/run_ws_daemon.py | Start WebSocket daemon | Canonical | Keep; call via task/run target | Core to your VS Code setup
scripts/ws_start.ps1 / ws_stop.ps1 / ws_status.py | Start/stop/status helpers | Supporting | Keep | Convenience wrappers around daemon
scripts/code_quality_checks.sh/.ps1 | One-shot lint+format+tests | Canonical | Keep; wire to CI | Your single, memorable quality gate
scripts/run_integration_tests.sh/.ps1 | Run integration tests | Supporting | Keep | Use when you specifically want local model/live tests
scripts/validate_quick.py | Fast smoke of core functionality | Supporting | Keep | Minimal, quick signal without full suites
scripts/ws_call_analyze.py / ws_call_chat.py / ws_exercise_all_tools.py | Programmatic MCP calls | Supporting | Prefer EXAI MCP; keep for automation | Useful for scripted CI steps
scripts/diagnose_mcp.py / ws_status.py | Basic health/status checks | Supporting | Prefer EXAI MCP status; keep | Good when EXAI MCP is unavailable
scripts/assess_all_tools.py | Assessment driver | Supporting | Prefer EXAI MCP analyze/codereview | Keep for bulk assessments
scripts/mcp_tool_sweep.py | Tool availability/latency snapshot | Supporting | Prefer EXAI MCP status/hub | Keep minimal
scripts/minimal_server.py | Minimal server for debugging | Supporting | Keep | Low-risk diagnostic fallback
scripts/smoke_tools.py / smoke_deferred_test.py / smoke_router_validator.py | Targeted smokes | Supporting | Prefer EXAI MCP targeted tests | Keep minimal
scripts/exai_agentic_audit.py / run_inline_exai_phase1_review.py | Doc-driven audits | Supporting | Prefer EXAI MCP analyze | Keep for batch automation
scripts/run_thinkdeep_web.py | Thinkdeep web-enabled path | Supporting | Prefer EXAI MCP thinkdeep | Keep for local experiments
scripts/mcp_e2e_* (auggie_smoketest, kimi, kimi_tools, paid_validation, smoketest) | E2E demos/validation | Deprecate | EXAI MCP: test plans under analyze/testgen | Add deprecation banner; fold useful parts into EXAI MCP docs
scripts/cleanup_phase3.* | Phase-specific cleanup | Deprecate | N/A | Add banner: superseded by current consolidation
scripts/demo_tools.py / tool_bench.py / alias_test.py / progress_test.py | Ad-hoc developer sandbox | Deprecate | N/A | Add banner; merge any still-useful snippets into docs/dev-notes
scripts/activate_*.ps1 / setup_venvs.ps1 | Env activation setup | Supporting | Keep | Document once; keep as convenience
scripts/coverage.sh/.ps1 | Coverage helpers | Supporting | Keep | Optional; wire into quality_checks if desired
scripts/clone_from_zen.ps1 / sync_exai.ps1 / exai_end_to_end.ps1 | Legacy cloning/sync/orchestration | Deprecate | EXAI MCP routes + gh-mcp | Add banner and sunset
scripts/exai_diagnose.py / validate_websearch.py / run_kimi_glm_audit_v4.py | Specialized diagnostics | Deprecate | EXAI MCP status/analyze/thinkdeep | Consolidate into EXAI flows

## Top‑5 canonical entry points (plain language)
1) Start/stop server for VS Code/Auggie: mcp_server_wrapper.py (and ws_start.ps1/ws_stop.ps1) — the normal way you run the MCP server locally.
2) Quick health/availability: EXAI MCP status/hub — fastest way to see providers, tools, and basic health.
3) Quality gate (before PR): code_quality_checks.sh/.ps1 — runs lint/format/tests in one go; hook this in CI.
4) Quick validation: validate_quick.py — fast pass without long tests; use when iterating locally.
5) Focused reviews and reports: EXAI MCP analyze / codereview / testgen — the preferred route to create audit/sweep reports and targeted tests.

