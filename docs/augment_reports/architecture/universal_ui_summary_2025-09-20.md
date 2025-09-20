## Universal UI Summary Architecture (2025-09-20)

### YES/NO Summary
YES — Designed a server-level UI wrapper (tool-agnostic) and GLM-4.5-flash manager parameters.

### Goals
- Provide a consistent UI block for every tool response without changing each tool
- Keep raw outputs intact and pass-through for logs and next-step chaining
- Use GLM-4.5-flash as the manager/first entry for classification and extremely simple answers

### Server-level wrapper (Mermaid)
```mermaid
flowchart LR
  Tool[Tool executes] --> Out[Raw ToolOutput]
  Meta[Metadata (duration, tokens, model, ids)] --> Wrap
  Out --> Wrap[Server UI Wrapper]
  Wrap --> UI[ui_summary (for display)]
  Out --> Raw[raw (for logs/next-step)]
```

### Proposed ui_summary schema (minimal, additive)
- step_number (optional)
- total_steps (optional)
- findings (optional)
- thinking_mode (optional)
- use_websearch (optional)
- model (best-effort)
- duration_secs (best-effort)
- tokens (best-effort)
- conversation_id (best-effort)
- expert_mode (best-effort)
- output.summary_bullets (derived dot-points)
- output.raw (verbatim)

### GLM-4.5-Flash as Manager: recommended defaults
- model: glm-4.5-flash
- temperature: 0.2 (deterministic manager behavior); use 0.0 for strict determinism
- top_p: 0.9 (balanced sampling when needed)
- max_tokens: 1536 (simple answers), 4096 (tool reasoning); fail-safe to 2048 if constrained
- streaming: true (faster perceived latency)
- tool_choice: auto
- parallel_tool_calls: true (where SDK supports)
- timeout_ms: 15000 for manager classification; up to 60000 for delegated/simple answers
- conversation_id: enabled (manager as information hub)
- memory strategy: summarize long dialogues into a rolling context; store key decisions and tool routing hints
- safety: moderate default; disallow self-escalation of cost without tool/router approval

Notes
- Values reflect manager goals (fast, deterministic first-hop). Tools may override.
- If SDK lacks certain knobs (e.g., penalties), omit without changing wrapper shape.

### Manager-first routing
```mermaid
flowchart LR
  U[User Prompt] --> M[GLM-4.5-flash Manager]
  M -->|Very simple| A1[Direct Answer]
  M -->|Else| P[Planner]
  P --> T{Select Tool}
  T --> Analyze
  T --> CodeReview
  T --> Debug
  T --> Precommit
  T --> Refactor
  T --> ThinkDeep
  ThinkDeep --> Orchestrate[GLM Browse || Kimi Files]
  Orchestrate --> Synthesize[Choose GLM/Kimi]
  Synthesize --> UIBlock[Server UI Wrapper]
```

### Storage posture (Manager as info hub)
- Maintain conversation_id for continuity
- Persist compact summaries of past steps (decision logs, chosen tools, models)
- Keep short-lived cache for tool descriptors and provider capabilities
- Do not store user files; delegate to provider-specific storage (Kimi) with retention policy

### Implementation notes
- Implement wrapper in server.py after each tool response is constructed
- Back-fill missing fields (duration, tokens) from ToolOutput.metadata if present; else skip
- Add one helper to derive summary bullets from text (first sentences or existing bullets)
- Keep feature-flag to disable wrapper if needed (for quick diffing)

