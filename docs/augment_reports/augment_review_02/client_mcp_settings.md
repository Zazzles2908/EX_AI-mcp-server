# Client MCP settings (recommended) — Validation/stability profile

One‑line YES/NO: YES — These settings prevent early client aborts during long/expert and multi‑file Kimi runs.

## TL;DR values
- MCP call timeout: 180s (minimum 150s)
- Expert fallback: OFF during validation for long/expert flows
- Progress keepalive: ~1500 ms (1.5s)
- Micro‑steps (server‑side): ON (already set in .env)

## Why these matter
- We observed TOOL_CANCELLED within 2–7s after expert/MF phases begin. Server was healthy and emitting heartbeats; the client wrapper aborted early.
- Raising the client call timeout and disabling proactive expert fallback prevents client‑side cancellations.

## VS Code (Augment) — example settings
If your extension exposes equivalent settings, set:

```jsonc
{
  // Allow long expert/MF calls to complete without client abort
  "augment.mcp.callTimeoutSec": 180,

  // Ensure UI stays alive while server runs expert/multi‑file logic
  "augment.mcp.progressKeepaliveMs": 1500,

  // Avoid client‑side auto‑fallback cancelling expert finals during validation
  "augment.tools.disableExpertFallback": true,

  // Optional: stagger heavy parallel starts to reduce contention
  "augment.mcp.parallelStartStaggerMs": 250
}
```

Notes:
- Names may differ per extension; use the closest equivalents (timeout, progress/heartbeat interval, expert fallback policy).
- Keep these values for validation runs. You can tune later once stability is proven.

## Server knobs already aligned
- EXAI_WS_CALL_TIMEOUT=180
- EXAI_WS_PROGRESS_INTERVAL_SECS=2.0
- EXAI_WS_EXPERT_MICROSTEP=true
- EXAI_WS_DISABLE_COALESCE_FOR_TOOLS includes kimi_multi_file_chat

## Validation checklist (after applying settings)
1) Restart VS Code Augment settings (you already did — thank you!)
2) Run a small multi‑file Kimi chat (1–2 markdown files) and confirm no TOOL_CANCELLED < 10s
3) Repeat with analyze/codereview expert=true micro‑steps ON; confirm early partials arrive and no cancellations occur

## Rollback
- If any instability appears, keep micro‑steps ON and increase call timeout to 180–240s temporarily while we inspect logs.

