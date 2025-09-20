## YES — Batch B/D/A applied; CI blocker live; docs updated

Summary (EXAI‑MCP)
- Provider/model: thinkdeep ping OK (model auto); chat not invoked this batch
- Call time: thinkdeep ~instant
- Cost: n/a (server did not report)
- ONE‑LINE: YES — Workspace healthy; import blocker added; src.tools removed from repo; docs updated

Changes in this batch
- A) Import blocker:
  - Added scripts/check_no_legacy_imports.py
  - CI: .github/workflows/ci.yml runs the blocker on each build
  - Fixed legacy imports in tools/consensus.py
- B) Remove ghost src/tools/:
  - Removed src/tools/__init__.py from repo (directory will vanish from Git; local __pycache__ may remain)
- D) Docs updates:
  - docs/o_and_m_manual/02_architecture.md: updated paths to src/providers and agentic router, added deprecation banner
  - docs/augment_reports/audit/removal_candidates.md: noted src/tools removal and CI blocker

Branch/Commit
- Branch: feat/phaseB-import-blocker-and-docs-cleanup
- Commit: chore(ci): add legacy import blocker; docs cleanup; audit updates

Next
- Sweep docs for any remaining providers.* references and add banners as needed
- Optional: add a pre-commit config for local dev convenience (mirrors CI check)


### Validation after restart (EXAI‑MCP)

Summary (EXAI‑MCP)
- Provider/model: chat → glm-4.5-flash (expected); thinkdeep → kimi-k2 (expected)
- Call time: not reported by server in tool responses
- Cost: not reported
- ONE‑LINE: YES — EXAI‑WS tools responded after restart (chat + thinkdeep)

Details
- chat: received a response (pong-equivalent). Tool response did not include model metadata.
- thinkdeep: request completed normally; tool response did not include model metadata.

Next batch queued: Phase C — Test sweep (unintentional legacy imports)
- Plan: scan tests for `from providers.` and `import providers.`; keep intentional shim tests; migrate unintended usages to `src.providers.*`; commit on current branch.
- Restart: not expected for doc/test-only migrations. I will notify if a restart is required.


### Phase C — Test sweep (Batch C1: providers import migration)

Summary (Batch outcome)
- ONE-LINE: YES — Migrated unintentional `providers.*` imports in key tests to `src.providers.*`; left intentional legacy/shim cases as-is.
- Scope: tests/test_kimi_glm_smoke.py, tests/test_provider_routing_bugs.py, tests/test_auto_mode_custom_provider_only.py, tests/conftest.py

What changed (by group)
- Providers core (canonicalize to src.providers):
  - tests/test_kimi_glm_smoke.py → registry/base/moonshot/zhipu now from src.providers.*
  - tests/test_provider_routing_bugs.py → base/registry and openrouter now from src.providers.* (kept gemini/openai_provider as legacy since those are optional/legacy-only modules)
  - tests/test_auto_mode_custom_provider_only.py → custom now from src.providers.custom
  - tests/conftest.py → custom/base in helper paths now from src.providers.* (top of file already used src.providers)
- Intentional legacy kept:
  - routing.*: tests/test_task_router_mvp.py retained as the dedicated shim test
  - optional providers (Gemini/OpenAI provider modules) left under legacy path per CI hygiene notes; these remain guarded/optional

Notes
- This is a batch migration aligned to Duplicate Domains Map and Decision Tree Architecture: canonical providers live under src/providers/*; top-level providers/* remains as a temporary shim/legacy home for optional modules.
- No server restart required for test-only import path adjustments.


### Phase C — Test sweep (Batch C2: routing import scan)

Summary (Batch outcome)
- ONE-LINE: YES — Only intentional legacy routing import found (tests/test_task_router_mvp.py). Kept as shim test by design.
- Scope: full tests/ scan for `from routing.` / `import routing.`

Notes
- All other tests already use `src.router.service` or `src.core.agentic.*`.
- No code changes required in this batch.


### Phase C — Test sweep (Batch C3: optional provider tests classification)

Summary (Batch outcome)
- ONE-LINE: YES — Introduced `optional_provider` pytest marker; tagged Gemini/OpenAI-dependent tests; preserved coverage where env is present.
- Scope: pytest.ini; tests/test_alias_target_restrictions.py; tests/test_provider_routing_bugs.py (targeted function)

What changed
- pytest.ini: added marker definition `optional_provider`
- tests/test_alias_target_restrictions.py: added module-level `pytestmark = pytest.mark.optional_provider`
- tests/test_provider_routing_bugs.py: added `@pytest.mark.optional_provider` to `test_mixed_api_keys_correct_routing` (the only test requiring Gemini/OpenAI presence)

Notes
- We chose targeted marking over broad file skipping to retain OpenRouter-only coverage inside the same module.
- CI can now deselect optional providers with `-m "not optional_provider"` if desired; tests still run locally when env keys are provided.
- No server restart required for these marker-only and import-clarity changes.


### Phase C — Script sweep (Batch C4)

Summary (Batch outcome)
- ONE-LINE: YES — scripts/ contained no legacy `providers.*` or `routing.*` imports requiring change; already canonical or server-config based.
- Scope: scripts/* (Python) scanned

Notes
- validate_quick.py and validate_websearch.py already use src.providers.*
- Other scripts import server/tools paths or are shell/PowerShell helpers without Python imports


### Phase D — Docs cleanup pass 2 (no restart required)

Summary (Batch outcome)
- ONE-LINE: YES — Updated CI notes to prefer `-m "not optional_provider"`; updated legacy_imports_scan.md with today’s migrations.
- Scope: docs/standard_tools/ci-test-notes.md; docs/augment_reports/audit/legacy_imports_scan.md

What changed
- CI/Test Hygiene Notes: recommend deselecting optional providers via marker and show example
- Audit: appended Update section with Phase C Batches C1–C3 migrations

Notes
- Historical docs under previous_audit/ were not modified (kept as historical source). Active audit source remains docs/augment_reports/audit/.
- No server restart required for documentation updates.
