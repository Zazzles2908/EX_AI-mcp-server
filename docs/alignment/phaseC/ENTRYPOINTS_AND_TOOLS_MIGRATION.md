# Phase C: Entry Points and Tools Migration (Draft)

Objective: Provide consistent entry points (console scripts) and begin migrating tools toward a unified module layout with optional import-compat shims.

## Console Entry Points (proposed)
- exai-mcp: launch main MCP server
- exai-ws-daemon: launch WebSocket shim/daemon

Benefits: consistent developer experience across platforms; future-proofing for packaging.

## Tools Layout
- Current: tools/ with many modules and a registry facade
- Target: consolidate under a single package path (e.g., src/ex_mcp_server/tools/)
- Transition: add short re-export shims at old paths while internal imports migrate

## Import-Compat Shims (what/why)
- Small files at the old import path that re-export the new symbols; zero logic
- Purpose: avoid breaking existing imports/tests during a gradual migration

Example shim:
```python
# tools/chat.py (shim)
from ex_mcp_server.tools.chat import ChatTool
__all__ = ["ChatTool"]
```

## Steps
1) Define canonical package path for tools (src/ex_mcp_server/tools)
2) Move 1–2 tools first (low-risk), create shims
3) Update internal imports to canonical path
4) Validate with unit/tests and quick runtime smoke (MCP tool-list)
5) Repeat in batches

## Validation
- [ ] Tools list renders in clients without duplicates
- [ ] No ImportError from legacy paths
- [ ] Minimal diff to registries; behavior unchanged


## Pilot Status (updated)
- Chat tool shim active: registry points to `src.tools.chat`
- Planner tool shim active: registry points to `src.tools.planner`
- Debug tool shim active: registry points to `src.tools.debug`
- Behavior unchanged: shims simply re-export original classes

## Next (incremental)
- Add 1–2 more tool shims, then batch-validate registry mapping
- After stable, evaluate flipping provider registry via staged Option B shim
