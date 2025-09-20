## Project Document Structure — Current (2025-09-20)

### YES/NO Summary
YES — Current top-level and key subfolders inventoried; duplicate domains and potential clashes noted.

### Top-level folders (selected) and purpose
- auggie: CLI and utilities for agentic runs (selectors, sessions, wrappers)
- context: context management helpers
- Daemon / src/daemon: websocket server and session management (src is canonical)
- docs: documentation, audits, architecture, reports
- monitoring: health, telemetry, autoscale helpers
- nl: natural-language command processor
- patch: portability patches and validation helpers
- providers (legacy): vestigial vendor folders (moonshot, zhipu); replaced by src/providers
- routing (legacy): vestigial; replaced by src/router
- scripts: smokes, diagnostics, helpers, wrappers
- security: RBAC and configs
- src: canonical application modules (providers, router, core, daemon, embeddings)
- streaming: adapters for streaming outputs
- supabase: keep
- systemprompts: prompt templates for tools/workflows
- templates: template content (auggie, etc.)
- tools: MCP-exposed tools and helpers (mix of entry tools and helper layers)
- ui: simple UI helpers
- utils: shared utility library (config, http, storage, tokens, metrics, etc.)

### Key duplicate/overlapping domains
- Providers
  - src/providers (canonical): base, registry, glm, kimi, openrouter, zhipu, etc.
  - providers/ (legacy): residual moonshot/zhipu subfolders and old __pycache__
  - Action: remove/deprecate top-level providers/ after confirming no imports
- Router
  - src/router/service.py (canonical)
  - routing/ (legacy, empty of code now)
  - Action: remove legacy routing/ after checks
- Tools
  - New subfolders under tools/: workflows, providers/{kimi,glm}, orchestrators, diagnostics, streaming, capabilities (canonical for MCP tools)
  - Top-level duplicate scripts removed; canonical modules are under subfolders; registry already points to them
  - Action: after a cooling period, replace top-level scripts with thin import shims or remove

### tools/ breakdown (current)
- Entry tools (subfolders, canonical now)
  - workflows/: analyze, codereview, debug, precommit, refactor, secaudit, testgen, planner, consensus, thinkdeep, tracer, docgen
  - providers/kimi/: kimi_upload, kimi_tools_chat, kimi_embeddings, kimi_files_cleanup
  - providers/glm/: glm_files, glm_agents, glm_files_cleanup
  - orchestrators/: autopilot, orchestrate_auto, browse_orchestrator
  - diagnostics/: diagnose_ws_stack, ws_daemon_smoke, toolcall_log_tail, health, status
  - streaming/: stream_demo, streaming_demo_tool, streaming_smoke_tool
  - capabilities/: version, listmodels, provider_capabilities, models, embed_router, recommend
- Helper layers (keep at tools/ root)
  - shared/, workflow/, unified/, reasoning/, cost/, simple/
- Still at tools/ root
  - No duplicate scripts remain after commit 35f5685; only helper layers (shared/, workflow/, unified/, reasoning/, cost/, simple/)

### Immediate risks
- Confusion from duplicate tool modules (root vs subfolders) — mitigated by registry pointing to subfolders
- Legacy providers/ and routing/ lingering — could confuse future imports

### Recommendation (current state)
- Keep registry pointing to subfolders (done)
- Duplicates at tools/ root removed in this branch (commit 35f5685). Run MCP smokes on this branch; after merge, no further duplicate cleanup is needed.
- Next: remove legacy providers/ and routing/ folders after a code search confirms no imports

### Mermaid (current top-level focus)
```mermaid
flowchart TD
  A[repo root] --> B[docs/]
  A --> C[src/]
  A --> D[tools/]
  A --> E[systemprompts/]
  A --> F[utils/]
  A --> G[monitoring/]
  D --> D1[workflows/]
  D --> D2[providers/{kimi,glm}/]
  D --> D3[orchestrators/]
  D --> D4[diagnostics/]
  D --> D5[streaming/]
  D --> D6[capabilities/]
  D --> D7[shared/, workflow/, unified/, reasoning/, cost/, simple/]
```

