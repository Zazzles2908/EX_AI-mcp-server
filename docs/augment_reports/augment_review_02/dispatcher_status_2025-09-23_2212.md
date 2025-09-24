# P2 — Dispatcher status (DRY‑RUN) — 2025-09-23 22:12

- YES — Dispatcher scaffolding present, env‑gated (EX_USE_DISPATCHER), DRY‑RUN logs wired; no routing changes enabled.

## What exists now
- src/server/dispatcher.py — placeholder class with route() no‑op
- server.py — env flag, guarded init, and DRY‑RUN logging in handle_call_tool
  - USE_DISPATCHER = os.getenv("EX_USE_DISPATCHER", "false") ...
  - _dispatcher = Dispatcher() if USE_DISPATCHER else None
  - DRY‑RUN: logs tool + model hint when _dispatcher present

## Acceptance for next phase (still non‑breaking)
- Extract a minimal resolve_model/tool routing function into Dispatcher, called under EX_USE_DISPATCHER but returning None (fallback to current path).
- Add telemetry hooks around route attempts.
- Keep behavior identical when EX_USE_DISPATCHER is off (default).

## Validation signals
- Startup: "Dispatcher initialized (scaffold) — no routing changes yet" (when enabled)
- Activity logs show DRY‑RUN events for tool calls

