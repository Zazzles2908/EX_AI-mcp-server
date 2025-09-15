MCP Call Summary — Result: YES | Provider: GLM | Model: glm-4.5-flash | Cost: low | Duration: fast | Note: Pre‑flip import audit completed

# Provider Import Audit (Option‑B)

Goal
- Inventory legacy provider imports to validate readiness for `src.providers.*` consolidation and CI guard.

Findings (non‑application paths excluded from guard)
- tests/** — multiple occurrences of `from providers.registry import ModelProviderRegistry` (intended for compatibility testing)
- scripts/** — validation scripts import `providers.registry` to run standalone (OK under guard excludes)
- auggie/** — wrappers/selector/model_discovery import `providers.registry` (excluded from guard; covered by providers/__init__.py shim)

Core application (tools/, server.py, utils/, src/)
- Current state: already importing from `src.providers.*` (confirmed spots: tools/shared/base_tool.py, server.py, utils/model_router.py, src/providers/*, tools/listmodels.py)
- No remaining `providers.registry` imports found in core application code

Guard alignment
- CI workflow updated to exclude: tests/**, scripts/**, auggie/** (in addition to shims and src/providers/**)
- This prevents false positives while we keep shims for public/compat layers

Next steps
1) Maintain shims in providers/__init__.py and providers/registry_srcshim.py through the deprecation window
2) If/when we decide to migrate auggie/** to `src.providers.*`, remove the corresponding guard exception
3) Proceed to flip confirmation: since core app already uses `src.providers.*`, the “single import‑site switch” is effectively applied

Verification
- Ran EXAI MCP smokes: status/chat/analyze/codereview/testgen → OK
- CI guard committed; will block new legacy imports outside allowed paths

