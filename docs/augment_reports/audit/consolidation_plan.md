# Consolidation Plan (Augment)

Status: Draft — Ready to execute in phases

Objectives
- Remove duplicate code paths, prevent drift, and simplify navigation
- Canonicalize domains: src/ for application code, tools/ for MCP tools, root for entrypoints

Principles
- Non-destructive first: import shims and deprecation banners before any deletions
- Observable safety: tests + smoke checks between each phase
- Rollback-friendly: each phase is independently revertible

Phase A — Providers canonicalization
- Canonical: src/providers
- Actions
  1) Add deprecation banner to top-level providers/*.py indicating src/providers is canonical
  2) Implement re-export shims in providers/__init__.py so `from providers.X import Y` resolves to `src.providers.X`
  3) Ensure server.py and tools already import from src.providers (they do); scan tests/scripts for `^from providers\.` and fix to src.providers where feasible
  4) Freeze top-level providers/* to read-only (no new features), update docs/providers README to point to src/providers
- Validation
  - Run focused tests: tests/test_openrouter_*.py, tests/test_xai_models.py, tests/test_thinking_routing.py
  - Manual smoke: tools.listmodels and a short chat via Kimi and GLM

Phase B — Routing unification
- Canonical: src/router/service.py for service-level routing; src/core/agentic/task_router.py for agentic heuristics
- Actions
  1) Move routing/task_router.py into src/core/agentic as task_router_legacy.py or merge into existing IntelligentTaskRouter
  2) Add routing/__init__.py shim re-exporting IntelligentTaskRouter from src.core.agentic
  3) Grep tests/scripts for `from routing.task_router` and switch to `from src.core.agentic.task_router`
- Validation
  - Run tests covering routing heuristics and thinking config: tests/test_thinking_routing.py, tests/test_model_thinking_config.py
  - Manual check: RouterService preflight logs models and auto selection paths

Phase C — Tools cleanup
- Canonical: tools/ directory
- Actions
  1) Confirm no source modules exist in src/tools/ (currently empty); remove src/tools package after import audit
  2) Keep tools/ as the sole source of MCP tool implementations; ensure server lean registry is the single constructor
- Validation
  - Run list_tools, basic chat/analyze/debug tool calls locally; ensure no import errors

Phase D — Documentation and guardrails
- Actions
  1) Update docs/architecture and docs/augment_reports to reflect canonical choices
  2) Add a CONTRIBUTING.md section: “Use src/providers and src/router only; do not add top-level provider files”
  3) Add CI lint to fail on new imports of `providers.` or `routing.` outside src/*

Detailed task breakdown
- Implement shims (A.2/B.2)
  - providers/__init__.py: `from src.providers import *` and module-level __all__ to mirror src
  - routing/__init__.py: `from src.core.agentic.task_router import IntelligentTaskRouter, TaskType`
- Search-and-replace (A.3/B.3)
  - Replace `from providers.` → `from src.providers.` in tests/ and scripts/
  - Replace `from routing.task_router` → `from src.core.agentic.task_router`
- Deprecation banners (A.1)
  - Add top-of-file comment: “DEPRECATED: Canonical implementation moved to src/providers/...; this file is frozen and will be removed in Phase F”

Deletions (final clean-up — Phase F)
- After 1–2 weeks of green CI and no legacy imports detected:
  - Delete providers/* duplicate files (keep package as shim if any external users rely on it)
  - Delete routing/task_router.py (if merged) and routing package (if unused)
  - Confirm src/tools/ removed

Risk and rollback
- Each phase is shim-first; revert by removing shim and changes in a single commit if issues arise
- Keep CHANGELOG entries and link to duplicate_domains_map.md for traceability

Execution notes
- Work on a feature branch off main, open a PR with: rationale, file list, validation logs, and rollback plan
- Prefer small PRs per phase
- Do not change runtime behavior (models/routes) — this is structural only

