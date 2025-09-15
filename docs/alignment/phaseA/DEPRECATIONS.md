# Phase A: Deprecation Banners (Draft)

This page documents scripts and docs considered deprecated for day-to-day usage. Nothing is deleted in Phase A; each item lists a preferred replacement and rationale.

> Banner pattern to place at top of deprecated files (where feasible):
>
> "DEPRECATED (Phase A): Prefer <replacement>. This file remains for historical compatibility. See docs/alignment/phaseA/SCRIPTS_SUPERSESSION.md for details."

## Scripts

- scripts/run_ws_daemon.py
  - Replacement: scripts/ws_start.ps1 (or ws_start.ps1 -Shim when using the shim)
  - Rationale: unified entry point with guardrails, restart handling, consistent .env loading

- scripts/run_ws_shim.py
  - Replacement: scripts/ws_start.ps1 -Shim
  - Rationale: same as above

- scripts/mcp_e2e_* (family)
  - Replacement: Prefer ws_* scripts for connectivity or pytest for tests
  - Rationale: reduce divergent flows; standardize on ws_* and pytest

- scripts/minimal_server.py, scripts/mcp_server_wrapper.py
  - Replacement: ws_start.ps1 and server.py
  - Rationale: reduce alternative launch paths that drift from main

## Documentation

- docs/external_review/auggie_cli_exai_repair_prompt.md
  - Replacement: docs/architecture/* (canonical) and docs/alignment/phaseA/*
  - Rationale: legacy direction; kept for history

- docs/external_review/auggie_cli_cleanup_prompt.md
  - Replacement: docs/architecture/* and docs/alignment/phaseA/*
  - Rationale: legacy direction; kept for history

Notes:
- These banners are documentation-only in Phase A. No behavior changes.
- Once confirmed, we can add the short banner text to the top of the listed files.

