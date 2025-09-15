# Phase A: Script Supersession Map (Draft)

Purpose: make it obvious which script to use for common tasks; retain specialized scripts for now, but prefer the primary entry points below.

Status: Draft for confirmation. After review, we can add short deprecation banners to superseded scripts and update READMEs.

## Primary entry points (recommended)

- Start/stop WS daemon or shim (Windows)
  - Preferred: `scripts/ws_start.ps1` (supports `-Shim`, `-Restart`)
  - Stops:    `scripts/ws_stop.ps1`
  - Supersedes calling Python modules directly for day-to-day use:
    - `scripts/run_ws_daemon.py` (use ws_start.ps1 instead)
    - `scripts/run_ws_shim.py`   (use ws_start.ps1 -Shim)
  - Why: one command with guard-rails, restarts safely, consistent working directory and .env loading

- Code quality checks (lint/format/tests)
  - Preferred: `scripts/code_quality_checks.sh` (Unix) or `scripts/code_quality_checks.ps1` (Windows)
  - Why: consistent pipeline (ruff/black/isort + tests) with unified outcomes

- Tests
  - Unit tests: `python -m pytest tests/ -v -m "not integration"`
  - Integration/Quick: `scripts/run_integration_tests.sh` or `scripts/validate_quick.py`
  - Why: standardized invocations minimize divergence and hidden flags

- Quick WS tool validation
  - Preferred: `scripts/ws_exercise_all_tools.py` or precise ones like `scripts/ws_call_chat.py`
  - Why: single place to exercise tool-list readiness

## Specialized scripts (kept; not primary)

- `scripts/mcp_e2e_*` family: historical e2e flows; prefer `ws_*` scripts or pytest where possible
- `scripts/demo_tools.py`, `scripts/progress_test.py`: targeted demos; keep for exploration
- `scripts/mcp_tool_sweep.py`, `scripts/assess_all_tools.py`: power-user diagnostics; not for day-to-day
- `scripts/minimal_server.py`, `scripts/mcp_server_wrapper.py`: internal or experimental launch modes
- `scripts/run_thinkdeep_web.py`: demo path; use sparingly

## Notes and Rationale

- A single, blessed path per common action reduces confusion and subtle environment differences.
- We did not remove functionality; this map only clarifies defaults.
- After confirmation, we can:
  1) Add short banners to non-preferred scripts pointing to the preferred entry point.
  2) Update README.md and docs/ to link to this page for new contributors.

