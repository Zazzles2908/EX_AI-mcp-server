# Removal Candidates (post-migration review)

Status: Do not delete yet. This list is for post-confirmation cleanup after the full import/routing conversion is complete.

## Legacy shim trees
- providers/* (top-level) — shim layer redirecting to src/providers/*
- routing/* (top-level) — now a thin shim to src/core/agentic/task_router.py; safe to remove post-green window

Rationale: Canonical code now lives under src/providers/* and src/router/* (plus src/core/agentic/*). Shims exist only for backward compatibility during migration.

## Legacy documentation/examples using old imports
- Any docs showing `from providers...` should be updated to `from src.providers...`

## Scripts likely to be consolidated or removed
- scripts/mcp_server_wrapper.py — keep if still the standard way to spawn stdio server; otherwise consolidate to server.py entrypoints
- scripts/mcp_e2e_smoketest.py — keep if useful; may merge into a single `scripts/smoke_all.py`
- scripts/diagnose_mcp.py — retain if actively used; otherwise fold diagnostics into a single validate script

## Tests that reference legacy paths (to be updated, not deleted)
- tests/test_provider_routing_bugs.py — update imports to `src.providers.*` once shims are removed

## Next steps before deletion
1) Confirm all non-test imports use `src.providers.*` and `src/router/*`
2) Run end-to-end MCP validations (stdio and WS)
3) After 1–2 weeks without regressions, schedule removal of shim directories
4) Replace or retire duplicate scripts with a single, documented smoke/health script

Owner: Augment Agent

## Newly updated in this pass (safe migrations confirmed)
- scripts/exai_agentic_audit.py — DEFAULT_FILES now points to `src/providers/registry.py`
- docs/standard_tools/adding_providers.md — all legacy `providers/*` references updated to `src/providers/*`

- scripts/validate_websearch.py — imports migrated to src.providers.*, smoke passed
- scripts/validate_quick.py — imports migrated to src.providers.*, tools/provider import check passes

- tools/selfcheck.py — migrated to src.providers.registry import

- auggie/wrappers.py — imports migrated to src.providers.base/registry
- auggie/model_discovery.py — imports migrated to src.providers.registry
- auggie/selector.py — imports migrated to src.providers.registry
- auggie/compare.py — imports migrated to src.providers.registry
- auggie/perf.py — imports migrated to src.providers.registry
- docs/standard_tools/adding_providers.md — best practices now reference src/providers/*

- src/providers/zhipu_optional.py — reverse shim removed; now an internal SDK-aware optional loader (no providers.* import)
- src/tools/ — removed in this pass (ghost; no imports found)


## Next candidates to remove (pending full confirmation)
- providers/* and routing/* shims after all imports/tests are updated to `src.*`

- Redundant validation wrappers once a single consolidated smoke script exists

