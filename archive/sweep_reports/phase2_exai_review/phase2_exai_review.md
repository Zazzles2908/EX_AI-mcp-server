# Phase 2 – EXAI Review of Reorg Plan

Summary of EXAI codereview feedback before executing file moves:

- Plan completeness: Adequate; covers providers, tools, and core. Keep shims to preserve entrypoints.
- Risks:
  - Import breakage: update providers.registry and tools imports in a single batch per layer.
  - Circular dependencies: ensure core/server does not import from tool subpackages; invert where needed via interfaces.
  - Tests and scripts: update PYTHONPATH usage in sweep/runner scripts to locate src/.
- Recommendations:
  - Create src/__init__.py and src/tools/__init__.py to ensure package discovery.
  - Add root-level server shim that sets PYTHONPATH to include src for safety on shell calls.
  - Move providers first, adjust registry imports, run sweep; then shared tool base; then workflow/simple.

Proceed with batch 1 (providers) and verify via sweep + EXAI codereview.
