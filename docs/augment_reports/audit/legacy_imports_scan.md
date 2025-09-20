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

Notes
- Many tests intentionally import from `providers.*` to validate the shimmed surface; this is acceptable during the migration window
- Tools generally import from `src.providers.*` already (e.g., tools/listmodels.py)

Next actions
- Keep the shim active until Phase F removal
- Where feasible in app code (non-tests), migrate imports to `src.providers.*`
- Add CI check (post-migration) to block new `providers.*` imports outside tests

