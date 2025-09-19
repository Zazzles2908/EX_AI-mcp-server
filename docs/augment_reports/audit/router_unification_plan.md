# Router Unification Plan (Phase B)

Goal: One authoritative routing path for model selection

Current state
- Service router: src/router/service.py (canonical service used by tools/server)
- Agentic router: routing/task_router.py and src/core/agentic/task_router.py (heuristics)

Risks
- Divergent heuristics between two task_router variants
- Ambiguity about when agentic hints should override or inform RouterService

Plan
1) Define ownership: RouterService is authoritative; agentic router provides hints only
2) Move/alias routing/task_router.py into src/core/agentic (deprecate routing/ for router logic)
3) Add explicit API: RouterService.accept_agentic_hint(TaskType, caps)
4) Logging: Record final decision and whether a hint was applied
5) Tests: Decision table tests for common TaskTypes (web, vision, long_context, code)

Validation
- Run targeted tests for RouterService decisions
- Enable DEBUG logs; confirm single decision path and hint application

