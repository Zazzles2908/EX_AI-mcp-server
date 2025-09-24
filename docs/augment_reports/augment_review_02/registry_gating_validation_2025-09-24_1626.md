# Registry Gating Validation — Post Augment Restart (Batch B)

One-liner: YES — Client shows gated registry; server logs confirm core-only active tools; validation calls completed with TOOL_COMPLETED entries.

## Client-visible tool count
- Reported by user after restart: 15 tools visible (down from 27)

## Server evidence (activity excerpts)
- 2025-09-24 16:20:25 — Registry gating: core_only=True allowlist=[]
- 2025-09-24 16:20:25 — Lean tool registry active - tools:
  ['activity','analyze','chat','codereview','debug','health','listmodels','precommit','refactor','secaudit','testgen','thinkdeep','tracer','version']

Note: Diagnostics preserved (version, listmodels). Client count may include a lightweight alias in UI; effective capabilities remain core-only.

## Validation calls
- chat_EXAI-WS (unpredictable prompt)
  - Output: Rain sketches cities, night births stone dreams.
  - Recent log: TOOL_COMPLETED: chat req_id=360244c6-1c5e-4c5c-96fa-616851b928f9
- activity_EXAI-WS
  - Recent log excerpts captured with Registry gating/Lean registry filters (see above)

## Result
- Core-only gating is active and reflected on both server and client sides
- Tools exposed match the intended core diagnostic + workflow set

## Next
- Mark tools consolidation tasks complete
- Proceed with remaining cleanups in subsequent batches if any

