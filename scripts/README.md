# scripts/ layout (standardized)

This repository standardizes scripts into clear subfolders while keeping backward compatibility.

## Canonical subfolders
- ws/ — WebSocket daemon and WS clients (daemon status, one-off chat, analysis helpers)
- validation/ — smoke tests and validators (tool exercisers, quick env checks)
- diagnostics/ — server/provider/router diagnostics and audits
- e2e/ — stdio MCP end-to-end client tests (auggie/MCP)
- kimi_analysis/ — Kimi/GLM coordination and audits
- tools/ — meta-utilities (version bump, CI scripts, venv, sync)
- legacy/ — quarantined items slated for removal after one cycle

## Backward compatibility
- Top-level shims now forward to the canonical subfolder and exit.
- Shims exist for: ws_chat_once.py, ws_status.py, ws_exercise_all_tools.py, ws_exercise_all_tools_noauth.py, validate_quick.py, validate_websearch.py, run_ws_daemon.py
- Please prefer invoking the scripts under their subfolders going forward.

## Next removal window
The following top-level items are duplicated and will be removed after the deprecation window unless referenced:
- ws_chat_once.py, ws_status.py, ws_exercise_all_tools.py, ws_exercise_all_tools_noauth.py, validate_quick.py, validate_websearch.py, run_ws_daemon.py

Other candidates (legacy): alias_test.py, tmp_registry_probe.py, cleanup_phase3.* , clone_from_zen.ps1, demo_tools.py, run_inline_exai_phase1_review.py

## Notes
- PowerShell helpers (activate_*, ws_*.ps1, integration test runners) remain at top-level for discoverability on Windows; they will get subfolder copies in a subsequent pass.
- See docs/augment_reports/augment_review/scripts_inventory.md and scripts_reorg_proposal.md for full mapping and plan.

