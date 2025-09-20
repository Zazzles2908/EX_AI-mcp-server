# Duplicate Domains Map (Augment)

Status: Populated (evidence-based) • Source: repo scan in this branch

Scope
- Targets: providers, routing/router, tools, core
- Goal: identify concrete file-level duplication and recommend a canonical home per domain

High-level summary
- Canonical recommendation: keep application code under src/, keep operational entrypoints at repo root, keep MCP tools under tools/
- Duplications confirmed: providers (heavy), routing (router vs agentic router), tools (ghost src/tools), minor core splits

Evidence by domain

1) Providers (duplicate implementations in two trees)
- Duplicated files (same class responsibilities, near-identical logic):
  - providers/openai_compatible.py ⇄ src/providers/openai_compatible.py
  - providers/registry.py ⇄ src/providers/registry.py
  - providers/glm.py ⇄ src/providers/glm.py
  - providers/kimi.py ⇄ src/providers/kimi.py
  - providers/zhipu_optional.py ⇄ src/providers/zhipu_optional.py
  - providers/moonshot/* ⇄ src/providers/moonshot/* (structure present under src)
- Notable drift examples:
  - openai_compatible.py: minor logging/headers differences and responses endpoint handling placement
  - registry.py: env variable compatibility improvements under src/ (e.g., vendor alias envs; resilient backoff vars)
- Risk: two registries and two base providers can diverge; imports in different parts of the app may point to different ones at runtime.

2) Routing vs Router (overlapping concerns)
- routing/task_router.py (IntelligentTaskRouter; context-length and web/vision rules) vs src/core/agentic/task_router.py (similar classification with different defaults)
- src/router/service.py (RouterService: preflight, choose_model, JSON decision logs). This is the canonical service used by server logic.
- Risk: two task_router variants with different heuristics may lead to different platform decisions depending on import site.

3) Tools
- tools/ contains complete tool implementations used by server.py and lean registry
- src/tools/ has only __init__.py and pycache artifacts; no source modules exist here
- Likely historical attempt to migrate; currently a ghost/placeholder

4) Core/Entrypoints
- server.py at repo root is the main MCP entrypoint with tool wiring and logging
- src/core contains agentic scaffolding (context manager, engine, hybrid manager) but not a separate server entrypoint
- No direct duplication here; split is acceptable if we define ownership boundaries

Canonical location recommendations
- Providers: src/providers (canonical). Top-level providers/ becomes a thin import-redirect shim (temporary) or is deprecated and removed after refactors.
- Routing: src/router for service, src/core/agentic for experimental agentic router. Move routing/task_router.py into src/core/agentic (as alias or merged) and deprecate routing/ folder for router logic.
- Tools: tools/ stays canonical. Remove src/tools/ from source (it’s empty) after verifying no imports reference it.
- Core: Keep server.py at root as entrypoint; keep core modules in src/core.

Immediate hotspots to audit for imports (to avoid mixed trees)
- server.py: uses src.providers.* and tools.* (good). Ensure no imports reference top-level providers.* inadvertently via older modules.
- tests/ and scripts/: search for imports of providers.* or routing.*; update to src.providers.* and src.router.* as needed.

Next actions (non-destructive)
1) Freeze top-level providers/ by adding deprecation headers in files and a README noting src/providers is canonical.
2) Add import shims under providers/__init__.py that re-export from src/providers to avoid breaking existing imports during migration.
3) Move routing/task_router.py into src/core/agentic or src/router and provide an import shim from routing/.
4) Remove src/tools/ (source) after confirming no imports; keep an empty package marker if needed, but prefer removal.

Validation plan
- Run unit tests focused on provider registry and routing selection to ensure a single code path is active.
- Grep for legacy imports (providers.*, routing.*) and fix in tests/scripts.
- Smoke: listmodels tool and small chat calls via Kimi/GLM to confirm providers resolve from src/providers.

Notes
- This map is intentionally conservative: we recommend redirection and deprecation before deletion.
- After shims are in place and CI is green for a week, plan final deletion of top-level duplicates.
