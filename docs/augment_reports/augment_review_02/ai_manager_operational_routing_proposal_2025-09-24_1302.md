# AI Manager — Operational routing proposal (toggle design and rollback)

One‑liner YES/NO: YES — Proposal documented; routing remains OFF by default; clear rollback strategy provided.

## Goal
Enable AI‑manager operational routing for select tools when explicitly toggled (ENABLE_SMART_CHAT=true AND EX_AI_MANAGER_ROUTE=true), while maintaining current safe defaults (advisory‑only).

## Toggles
- ENABLE_SMART_CHAT (default: false)
- EX_AI_MANAGER_ROUTE (default: false)
- EX_AI_MANAGER_ADVISORY (default: true)
- SAFE_GUARD_MCP_TOOLS: allowlist of tools eligible for routing (default: empty)

## Routing decision flow (when toggled on)
1. If tool ∉ SAFE_GUARD_MCP_TOOLS → bypass (no routing)
2. Build manager plan (think + cost estimation)
3. If plan risk > threshold → bypass (log advisory only)
4. If plan ok → translate arguments → call target provider/tool
5. Always emit MCP_CALL_SUMMARY and RESPONSE_DEBUG with `ai_manager_plan`

## Guardrails
- Hard cap per‑attempt timeout ≤ EXAI_WS_CALL_TIMEOUT
- No fan‑out; exactly one routed attempt per call
- Respect DISABLED_TOOLS and LEAN_MODE registry constraints

## Rollback plan
- Single switch: set EX_AI_MANAGER_ROUTE=false → immediate revert to advisory‑only
- Fallback to original tool path preserved (non‑destructive)
- Log `ai_manager_route_rollback` event when toggled off after failures

## Validation plan
- Shadow test with ENABLE_SMART_CHAT=true and EX_AI_MANAGER_ROUTE=false (advisory only)
- Canary enable with SAFE_GUARD_MCP_TOOLS={chat} in a local branch
- Verify activity log for plan + routed calls; ensure zero TOOL_CANCELLED inflations

## Status
- Current default: advisory‑only (no routing). This proposal adds a safe, gated pathway that can be flipped on with clear rollback.

