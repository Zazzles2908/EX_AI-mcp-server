# Phase 5 (P5) — Manager routing (env‑gated), smart_chat registration, native stubs

- YES — Implemented env‑gated routing and optional registrations. Restarted and validated ON/OFF behavior with real outputs.

## Changes made
- server.py
  - Added EX_AI_MANAGER_ROUTE flag and operational routing in handle_call_tool (env‑gated)
  - Post‑registry optional registration: SmartChat tool when ENABLE_SMART_CHAT=true
  - Optional native provider stub loads (not wired): ENABLE_ZHIPU_NATIVE / ENABLE_MOONSHOT_NATIVE
- tools/smart/smart_chat.py
  - Renamed get_name() → "smart_chat" to avoid collision; advisory‑only
- .env (updated)
  - EX_AI_MANAGER_ROUTE=true (for P5 ON validation; default was false)
  - ENABLE_SMART_CHAT=true (to expose tool; advisory‑only)

## Validations

A) Routing OFF (EX_AI_MANAGER_ROUTE=false)
- GLM chat nonce: sable-bear-88aa (real)
- Kimi multi-file chat nonce: onyx-tern-2e7d (real)
- Logs: ai_manager_plan present; no ai_manager_route entries (expected OFF)

B) Routing ON (EX_AI_MANAGER_ROUTE=true)
- GLM chat nonce: ruby-otter-71a2 (real)
- Kimi multi-file chat nonce: cobalt-ibis-5d9f (real)
- SmartChat: registered (log confirms)
- Note on route logs: For these two calls, manager suggested tools matched originals (chat→chat, kimi_multi_file_chat→kimi_multi_file_chat), so no ai_manager_route event was needed. Model hints were injected only if not explicit.

Server restarts
- All changes applied with ws_start.ps1 -Restart; daemon healthy on ws://127.0.0.1:8765

## Observations
- Parity preserved with routing OFF (identical behavior to P4)
- With routing ON, behavior remains stable; route decisions fall back to identity mapping for these test shapes; logs retain ai_manager_plan and RESPONSE_DEBUG
- SmartChat tool available (advisory text) without impacting existing chat tool

## Next steps (follow‑up)
- Expand tests to include a case where tool selection differs (e.g., manager suggests Kimi but request came via generic path) to exercise ai_manager_route event
- Consider wiring native providers minimally for a single happy‑path function under flags to validate registration path end‑to‑end

