# Legacy Imports Scan (providers.*)

Summary
- Goal: Identify usages of legacy `providers.*` imports for deprecation planning
- Method: Codebase retrieval and grepping targeted modules

Initial findings (examples)
- tests/test_templates_default_integration.py
- tests/test_registry_fallback.py
- tests/test_provider_routing_bugs.py
- tests/conftest.py
- tests/mock_helpers.py
- tests/helpers/free_first_registry_check.py
- scripts/validate_quick.py
- scripts/validate_websearch.py


Status updates (migrated in this pass)
- scripts/validate_quick.py  now uses src.providers.*
- scripts/validate_websearch.py  now uses src.providers.*
- tools/selfcheck.py  now uses src.providers.registry

- auggie/wrappers.py  now uses src.providers.base and src.providers.registry
- auggie/model_discovery.py  now uses src.providers.registry
- auggie/selector.py  now uses src.providers.registry
- auggie/compare.py  now uses src.providers.registry
- auggie/perf.py  now uses src.providers.registry

Notes
- Many tests intentionally import from `providers.*` to validate the shimmed surface; this is acceptable during the migration window
- Tools generally import from `src.providers.*` already (e.g., tools/listmodels.py)

Next actions
- Keep the shim active until Phase F removal
- Where feasible in app code (non-tests), migrate imports to `src.providers.*`
- Add CI check (post-migration) to block new `providers.*` imports outside tests


Updates (2025-09-20 — Phase C Batches C1–C3)
- tests/test_kimi_glm_smoke.py → migrated to src.providers.*
- tests/test_provider_routing_bugs.py → base/registry/openrouter migrated to src.providers.*; Gemini/OpenAI kept legacy imports (optional)
- tests/test_auto_mode_custom_provider_only.py → custom migrated to src.providers.custom
- tests/conftest.py → helper imports aligned to src.providers.*
- pytest.ini → added optional_provider marker; selective tagging applied in tests

