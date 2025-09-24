# Scripts Reorg Plan (Scaffolding) — 2025-09-23 21:19

- YES — Canonical subfolders verified/created; wrapper/shim plan prepared (no moves yet).

## Canonical folders (present)
- scripts/validation — smoke + bench + ws exercises (README present)
- scripts/diagnostics — router/service diagnostics (README present)
- scripts/ws — daemon + ws chat utilities (README present)
- scripts/e2e — end-to-end flows (README present)
- scripts/tools — helper utilities (README present)
- scripts/kimi_analysis — Kimi/Moonshot analysis (README added in this step)
- scripts/legacy — (to be added when moving deprecated scripts)

## To-be-moved (examples)
- Top-level scripts that belong under subfolders:
  - mcp_e2e_auggie_smoketest.py → e2e/
  - mcp_e2e_kimi.py → e2e/
  - mcp_e2e_kimi_tools.py → e2e/
  - mcp_e2e_paid_validation.py → e2e/
  - mcp_e2e_smoketest.py → e2e/
  - ws_chat_*.py → ws/
  - ws_exercise_all_tools*.py → validation/
  - validate_quick.py, validate_websearch.py → validation/
  - router_service_diagnostics_smoke.py → diagnostics/
  - show_progress_json.py → diagnostics/
  - run_ws_daemon.py → ws/

## Backward-compatible shims (plan)
- Leave thin trampoline files at old locations that import and delegate to the new path, e.g.:
  - from scripts.validation.ws_exercise_all_tools import main; if __name__ == "__main__": main()
- Keep shims for one release cycle, add deprecation banner, then remove.

## Safety/Validation
- After batched moves, restart WS daemon and run:
  - EXAI-WS: activity (review startup) + a quick chat/analyze call to confirm tool registry unaffected
- Update this plan with any path conflicts observed.

## Next actions (P2)
1) Stage trampoline shims for a small subset (ws_exercise_all_tools, ws_chat_once)
2) Move a minimal safe batch and validate
3) Commit as a single block

