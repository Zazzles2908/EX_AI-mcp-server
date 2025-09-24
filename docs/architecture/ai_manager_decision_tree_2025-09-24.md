# AI Manager Decision Tree (P4 Batch 2)

- Scope: Non-operational planning. Manager remains off by default; when enabled, logs only.
- Goal: Define clear routing decisions, provider roles, and safety fallbacks without changing runtime behavior yet.

## Decision Tree (Mermaid)
```mermaid
graph TD
  A[Start: Tool call + arguments] --> B{Need structure/depth?}
  B -->|No_Simple_NoFiles| C[GLM_chat]
  B -->|Yes| D[Planner_Analyze_ThinkDeep]
  D --> E{Files_attached?}
  C --> F{Web_search_requested?}
  F -->|Yes| G[GLM_websearch_branch]
  F -->|No| H[Return_GLM_response]
  E -->|Yes| I[Kimi_multifile_chat_attachment_first]
  E -->|No| J[Return_analysis_output]
  I --> K{Large_context_required?}
  K -->|Yes| L[Kimi_reasoning_caching_path]
  K -->|No| M[Direct_answer]
  I --> N{Tool_calls_needed?}
  N -->|Yes| O[Kimi_chat_with_tools]
  N -->|No| M
  %% Safety and fallback
  subgraph "Safety Net"
    P[Circuit_breakers] --> Q[Fallback_orchestrator]
  end
  C --> P
  I --> P
  O --> P
```

## Provider roles & constraints
- GLM (manager-fast path): quick replies, websearch-capable, low cost.
- Kimi (attachment-first): robust with files, better caching/retrieval, reasoning modes when required.
- Fallback orchestrator engages on provider failure; circuit breakers prevent thrashing.

## Integration plan (no-op hooks)
- server.handle_call_tool calls AiManager.plan_or_route(tool, args) in DRY-RUN (already logs-only).
- Next phase: return advisory hints (model, websearch, attach flags) but keep default behavior unless env gates allow.

## Acceptance criteria for P4 (scaffolding stage)
- [ ] Decision tree documented (this file) with clear provider roles and fallbacks.
- [ ] Env remains off-by-default; enabling logs-only produces trace lines without changing results.
- [ ] Server restarts clean; validations pass with real model outputs and file_id paths.
- [ ] No changes to tool schemas or observable behavior for users.

## Notes
- Keep Moonshot base_url=https://api.moonshot.ai/v1.
- Maintain attachment-first policy; limit fallback inline content to 50KB.

