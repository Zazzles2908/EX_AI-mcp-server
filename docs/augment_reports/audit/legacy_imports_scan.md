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


- monitoring/health_monitor_factory.py — now uses src.providers.hybrid_platform_manager
- tools/consensus.py — provider imports migrated to src.providers.registry
- utils/conversation_memory.py — provider imports migrated to src.providers.registry
- simulator_tests/conversation_base_test.py — provider import migrated for in-process tool runner
- patch/patch_crossplatform.py — patched embedded test content to src.providers.registry


Status updates (this pass)
- tests/conftest.py — base/custom now from src.providers.*
- tests/test_kimi_glm_smoke.py — migrated to src.providers.(registry,base,kimi,glm)
- tests/test_auto_mode_custom_provider_only.py — migrated to src.providers.(base,registry,custom)
- tests/test_provider_routing_bugs.py — uses src.providers for (base,registry,openrouter); gemini/openai imports intentionally left legacy (upstream optional providers)

Validation
- Non-test legacy import blocker: PASS locally and enforced in CI

Notes
- Many tests intentionally import from `providers.*` to validate the shimmed surface; this is acceptable during the migration window
- Tools generally import from `src.providers.*` already (e.g., tools/listmodels.py)

- OpenRouter-focused tests are skipped by default unless OPENROUTER_TESTS_ENABLED=true
- Mixed-keys routing test is skipped when providers.gemini is unavailable in this fork

Next actions
- Keep the shim active until Phase F removal
- Where feasible in app code (non-tests), migrate imports to `src.providers.*`
- Add CI check (post-migration) to block new `providers.*` imports outside tests

