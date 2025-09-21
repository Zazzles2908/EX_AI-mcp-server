# Project Tree (focused on MCP tools and core runtime) — 2025-09-21

## tools/workflows/
- analyze.py
- codereview.py
- consensus.py
- debug.py
- docgen.py
- planner.py
- precommit.py
- refactor.py
- secaudit.py
- testgen.py
- thinkdeep.py
- tracer.py

## tools/providers/kimi/
- kimi_embeddings.py
- kimi_files_cleanup.py
- kimi_tools_chat.py
- kimi_upload.py

## tools/providers/glm/
- glm_agents.py
- glm_files.py
- glm_files_cleanup.py

## tools/diagnostics/
- batch_markdown_reviews.py
- diagnose_ws_stack.py
- health.py
- ping_activity.py
- status.py
- toolcall_log_tail.py
- ws_daemon_smoke.py

## tools/orchestrators/
- autopilot.py
- browse_orchestrator.py
- orchestrate_auto.py

## src/providers/
- __init__.py
- base.py
- capabilities.py
- custom.py
- glm.py
- hybrid_platform_manager.py
- kimi.py
- metadata.py
- openai_compatible.py
- openrouter.py
- openrouter_registry.py
- registry.py
- moonshot/ (pkg)
- zhipu/ (pkg)
- zhipu_optional.py

## src/router/
- service.py

## src/daemon/
- session_manager.py
- ws_server.py

## Registry & Server
- tools/registry.py (lean registry; TOOL_MAP + TOOL_VISIBILITY)
- tools/__init__.py (exports tool classes)
- server.py (main MCP server; registry integration; handlers)

