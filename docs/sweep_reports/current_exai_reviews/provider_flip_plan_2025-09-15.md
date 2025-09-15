MCP Call Summary — Result: YES | Provider: GLM | Model: glm-4.5-flash | Cost: low | Duration: fast | Note: Option‑B provider flip plan drafted

# Provider Consolidation Plan (Option‑B)

Status
- CI guard added: .github/workflows/provider-import-guard.yml (blocks legacy `providers.*` imports outside approved shims/tests/scripts)
- Next: complete pre‑flip audit and switch the single import site to src.providers.registry


Goal
- Migrate all provider imports to src.providers.registry with a single flip point and CI guard, keeping behavior intact.

Flip point (single import site)
- Today: some modules import from providers.registry; others from src.providers.registry (via shim staged).
- Plan: choose one canonical module (e.g., tools/providers.py or providers/__init__.py consumer) to import only from src.providers.registry and fan out from there.

Steps
1) Add guard: CI rule to fail when code contains `from providers.` (except the shim file) once flip is live.
2) Pre‑flip audit: run codebase search to list all provider imports; ensure every tool uses the canonical import path indirectly.
3) Flip: update the single import site to src.providers.registry.
4) Bake: run quick smokes (status/chat/analyze/codereview/testgen) and verify MCP Call Summary stamps provider/model.
5) Clean: keep providers/registry_srcshim.py for one release; mark deprecated with banner.

Observability
- Ensure every tool response includes provider/model in the MCP Call Summary.
- Add a DEBUG log line when the router resolves model → provider.

Rollback
- If any tool fails, revert the single import site to the former path; retest. Low blast radius.

