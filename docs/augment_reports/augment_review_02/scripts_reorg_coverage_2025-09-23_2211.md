# P2 — Scripts reorg coverage — 2025-09-23 22:11

- YES — Canonical locations present; top‑level shims have deprecation banners; no missing wrappers found in sampled set.

## Canonical folders
- scripts/ws — ws_chat_once.py, run_ws_daemon.py, etc.
- scripts/validation — validate_quick.py, ws_exercise_all_tools(_noauth).py
- scripts/diagnostics — router_service_diagnostics_smoke.py, provider checks
- scripts/kimi_analysis — README added

## Top-level shims updated (banners)
- scripts/ws_exercise_all_tools.py
- scripts/ws_exercise_all_tools_noauth.py
- scripts/ws_chat_once.py
- scripts/run_ws_daemon.py
- scripts/router_service_diagnostics_smoke.py
- scripts/validate_quick.py

## Decision
- Keep shims for back‑compat this phase; consider slimming to pure trampolines in a later cleanup pass.

## Next
- Tool description/visibility: continue cleanup where needed
- Server modularization: document dispatcher DRY‑RUN status and next wiring plan

