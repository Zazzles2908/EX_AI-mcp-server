# Tools consolidation map (design + gated scaffold)

One-line YES/NO: YES — Consolidation plan drafted; gated scaffolds to follow.

## Canonical tool set (retain; stabilize)
- activity, analyze, challenge, chat, codereview, debug, docgen, listmodels, planner, precommit, provider_capabilities, refactor, secaudit, testgen, thinkdeep, tracer, version

## Manager-facing wrappers (advisory-only now)
- smart_chat (plan-first, advisory)
- file_chat (planned) — will reuse kimi_upload_and_extract or local file reads; normalize messages

## Defer/remove candidates (post-migration)
- glm_agent_* family once native adapters land and parity is proven

## Registry policy
- Keep visibility tiers: user-visible vs manager-only vs backend
- Maintain coalescing-disable list for long/expert tools (analyze, codereview, testgen, thinkdeep, debug)

## Next steps
1) Implement smart_chat advisory wrapper (no routing changes) — gated by ENABLE_SMART_CHAT
2) Add file_chat wrapper that accepts files and emits normalized messages
3) Migrate individual tools to shared response_envelope utilities (phase 2+)
4) Validate with EXAI‑WS sweeps; log MCP_CALL_SUMMARY deltas

