# Phase 2 – Reorganization Plan

This document proposes the directory structure and the stepwise move plan. No files are moved yet.

## Target structure
- src/
  - core/
    - server/ (handlers, runtime)
    - config.py, constants.py
    - utils/
  - tools/
    - workflow/ (analyze, codereview, refactor, secaudit, planner, docgen, debug, consensus, precommit, testgen)
    - simple/ (chat, version, listmodels, activity)
    - analysis/ (thinkdeep, tracer)
    - shared/ (base_tool, schema_builders, validators)
  - providers/
    - base.py, registry.py
    - glm/, kimi/, openrouter/, custom/
  - clients/
    - claude/, augment_cli/, augment_code/, vscode/
- scripts/
- docs/
  - guides/ (per-client setup)
  - tools/
  - sweep_reports/
- examples/
- tests/

## Compatibility
- Keep repo-root server.py as a shim importing src/core/server
- Maintain existing entrypoints and script calls; update paths gradually

## Stepwise moves (batches)
1) Prepare src/ skeleton and import shims.
2) Move providers/* into src/providers/*; update imports in registry.
3) Move tools/shared/* and base_tool into src/tools/shared/*; adjust imports in tool modules.
4) Move workflow tools into src/tools/workflow/* and simple/analysis accordingly.
5) Introduce src/core/server package and move non-shim server internals into it.
6) Update run-server scripts to prefer new paths (keep old for compat).

After each batch: run sweep and EXAI codereview; generate timestamped reports.
