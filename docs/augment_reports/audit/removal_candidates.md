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

### Detailed file list (shim removal plan)

Providers shim (top-level providers/ — remove entire directory after stabilization). Files to delete:
- providers/__init__.py
- providers/balancer.py
- providers/base.py
- providers/glm.py
- providers/hybrid_platform_manager.py
- providers/kimi.py
- providers/openai_compatible.py
- providers/registry.py
- providers/zhipu_optional.py
- providers/moonshot/provider.py
- providers/zhipu/provider.py

Routing shim (top-level routing/ — remove entire directory after stabilization). Files to delete:
- routing/task_router.py

Notes

## Phase‑F deletion rollup (after stabilization window)
- Delete entire providers/ directory (top-level shim tree)
- Delete entire routing/ directory (top-level shim tree)
- Confirm src/tools/ remains removed (ghost)

Caveats
- If external users import providers.* explicitly, keep a minimal providers/__init__.py that raises a clear ImportError with migration instructions. Otherwise remove wholesale.
- Preserve CHANGELOG entries and link this file in the PR description for traceability.

- __pycache__ directories and .pyc files are runtime artifacts and are not tracked; they will be removed automatically when deleting directories.
- Keep this list as the authoritative deletion checklist for the post-green window.


## Phase‑F removal status (feat/phaseF-shim-removal)
- Status: The following shim files have been deleted in the Phase‑F branch:
  - providers/__init__.py
  - providers/balancer.py
  - providers/base.py
  - providers/glm.py
  - providers/hybrid_platform_manager.py
  - providers/kimi.py
  - providers/openai_compatible.py
  - providers/registry.py
  - providers/zhipu_optional.py
  - providers/moonshot/provider.py
  - providers/zhipu/provider.py
  - routing/task_router.py
- Residual directories: providers/, routing/ now contain only __pycache__/ artifacts locally; these are not tracked by git and disappear after directory deletion in the PR.
- Canonical sources: all implementations live under src/providers/* and src/router/*.

- providers/* and routing/* shims after all imports/tests are updated to `src.*`

- Redundant validation wrappers once a single consolidated smoke script exists



Notes (this pass)
- OpenRouter-focused tests are skipped by default unless OPENROUTER_TESTS_ENABLED=true (optional upstream; avoids network/config flakiness during consolidation)
- Gemini mixed-keys routing test is skipped if providers.gemini is not present in this fork
