# Phase 3 – Manager‑First Architecture (Design and Implementation Plan)

Status: DRAFT (implementation-ready; will request one daemon restart after code batch)
Date: 2025-09-21

Objective
- GLM‑4.5‑flash acts as manager/router: classify intent, select tool, orchestrate provider handoff, manage continuation_id, and minimize cost.

Key components
1) Router service (src/router/service.py)
   - Add classify→delegate flow (simple heuristics + env‑gated rules)
   - Respect ALLOWED_PROVIDERS and routing profile (speed/balanced/quality)
   - Attach route_diagnostics (when ROUTER_DIAGNOSTICS_ENABLED=true)
2) Server integration (server.py)
   - Ensure router paths are callable by chat/analyze; preserve existing direct calls
   - Standardize ui_summary when enabled; aggregate text when EXAI_WS_COMPAT_TEXT=true
3) Provider orchestration
   - Default: GLM‑flash for simple/short tasks; Kimi for long‑context workflows
   - Honor fallback order and retries; surface clear errors on misconfig
4) Continuation & timeouts
   - Normalize continuation_id across workflows; add heartbeat where missing
   - Apply TOOL_EXEC_TIMEOUT_SEC + per‑workflow overrides

Implementation steps (batched)
- Add routing helpers to src/router/service.py (no breaking changes)
- Minimal glue in server.py to invoke router for manager‑requested paths
- Leave tools unchanged except for optional ui_summary harmonization

Validation plan (Phase 4)
- Smoke: listmodels, chat, analyze, thinkdeep (unpredictable prompts)
- Router checks with route_diagnostics enabled; capture logs
- Per‑folder minimal tool runs; verify schemas/outputs

Restart note
- I will request a single EXAI‑WS daemon restart after committing the router+server batch so changes take effect.

