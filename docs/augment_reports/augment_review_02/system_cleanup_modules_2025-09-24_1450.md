# System Cleanup — server module evaluation (response_handler, model_resolver, mcp_protocol)

One-liner: YES — Added import-safe, minimal stubs aligned with cleanup goals; no wiring changes yet.

## What was added
- src/server/response_handler.py — emits standardized MCP summary/debug lines via utils.response_envelope (import-safe fallback)
- src/server/model_resolver.py — conservative resolver with DEFAULT_MODEL=glm-4.5-flash
- src/server/mcp_protocol.py — tiny normalization helpers (messages array, chat message shape)

## Rationale
- Keep server.py thin, centralize concerns behind light modules
- Import-safe to avoid breaking partial environments; easy to wire later
- Aligns with external_review/system_cleanup_plan.md (modularization without behavior change)

## Next
- Evaluate integration points in dispatcher/registry_bridge; gate behind env vars
- Add unit tests if modules become wired

