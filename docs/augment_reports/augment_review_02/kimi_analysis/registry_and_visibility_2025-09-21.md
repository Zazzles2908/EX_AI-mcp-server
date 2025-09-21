# Phase 1 – Registry & Visibility Analysis (Kimi)

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Registry snapshot (tools/registry.py)
- Core: chat, analyze, debug, codereview, refactor, secaudit, planner, tracer, testgen, consensus, thinkdeep, docgen, precommit, challenge
- Utilities: version, listmodels, self-check (hidden unless DIAGNOSTICS=true), provider_capabilities, activity, toolcall_log_tail
- Orchestrators: autopilot, browse_orchestrator (alias), orchestrate_auto (hidden)
- Kimi: kimi_upload_and_extract, kimi_multi_file_chat, kimi_chat_with_tools
- GLM: glm_upload_file, glm_multi_file_chat, glm_agent_chat, glm_agent_get_result, glm_agent_conversation
- Streaming demo: stream_demo

Visibility map (TOOL_VISIBILITY)
- core: status, chat, planner, thinkdeep, analyze, codereview, refactor, testgen, debug, autopilot
- advanced: provider_capabilities, listmodels, activity, version, kimi_*, glm_*, consensus, docgen, secaudit, tracer, precommit, stream_demo
- hidden: toolcall_log_tail, health, browse_orchestrator, orchestrate_auto

Gating flags
- LEAN_MODE=false by default; DEFAULT_LEAN_TOOLS includes chat/analyze/planner/thinkdeep/version/listmodels
- DISABLED_TOOLS= (empty)
- STRICT_LEAN=false; DIAGNOSTICS=false hides self-check

Known/likely mismatches
- IDE calls may use alias suffixes (e.g., chat_EXAI-WS)  now handled by WS alias normalization
- Tools outside TOOL_MAP will not be exposed (verify imports after reorg)

Actions
1) Run list_tools from server to confirm parity with TOOL_MAP and VISIBILITY
2) Ensure DISABLED_TOOLS and LEAN_MODE produce expected filtered toolset
3) Add missing descriptors if any tools get_descriptor fails
4) Validate hidden/advanced visibility behavior in client menus

This section will be replaced by the authoritative Kimi analysis output once received.
