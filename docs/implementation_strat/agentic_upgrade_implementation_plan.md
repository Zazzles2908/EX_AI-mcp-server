# EX_AI MCP Agentic Upgrade: Architecture Mapping, Tool Rationalization, and Registry Renaming

This plan fully aligns with:
- docs/external_review/auggie_cli_agentic_upgrade_prompt.md
- docs/external_review/auggie_cli_cleanup_prompt.md

It consolidates tools, renames the tool registry for clarity, and preserves user-friendly ergonomics with high capability.

---

## 1) Target Architecture (adopted from Auggie prompts)

Adopt the following components and map them to our current codebase for incremental implementation:

- HybridAgenticMCPServer → maps to server.py + tools orchestration
- IntelligentTaskRouter → new ModelRouter utility (GLM/Kimi selection + escalation)
- AdvancedContextManager → enhance utils/conversation_memory.py + token budgeting in BaseTool
- ResilientErrorHandler → central exception categorization + retry/fallback wrappers around providers
- AdaptiveConfiguration → env-driven toggles (expert analysis shim added in utils/expert_analysis_config.py)
- SecureInputValidator → path/content validators for chat/analyze tools
- UnifiedToolManager (rename of current Registry) → own section below

---

## 2) Tool rationalization (remove/merge/keep)

Based on "Cleanup Prompt" guidance:

- Consensus legacy
  - Action: deprecate legacy consensus-specific modules. Keep the Consensus tool name for compatibility but re-implement as a thin wrapper over AutonomousWorkflowEngine (future) with a deprecation notice.
  - Why: Broken validation and overlapping intent with workflows.

- Assessment infrastructure legacy
  - Action: remove bespoke expert-analysis parsing/continuation; rely on workflow tools’ standard outputs and the new expert_analysis_config shim. Collapse multiple schema layers into one.
  - Why: Over-engineered chains, brittle parsing.

- Analyze over-engineering
  - Action: allow flexible step counts (no forced 3-step); keep Phase 1 local (no external model) and final optional expert step with ≤10 files. Maintain progressive disclosure of parameters.
  - Why: Lower cost, higher effectiveness per the prompts.

- Chat security issues
  - Action: add SecureInputValidator for file paths and input-size checks in chat/multi-file tools. Sandbox absolute paths.
  - Why: Address path injection/insecure file access risks called out in prompts.

- Activity/Status redundancy
  - Action: converge on status + activity (logs) with structured output; avoid raw text-only modes.
  - Why: Prompts advocate structured, reliable monitoring.

- Challenge tool bloat (if present)
  - Action: limit descriptions (<200 chars), centralize prompt templates, remove duplicated schemas.
  - Why: Reduce cognitive load, match progressive disclosure.

Tools to KEEP (lean): chat, analyze, codereview, debug, planner, precommit, refactor, secaudit, status, testgen, tracer, consensus (as thin wrapper, marked DEPRECATED).

---

## 3) Registry renaming and role

Rename the tool registry to reflect cross-platform, chain-aware management.

- File rename (planned): tools/registry.py → tools/tool_hub.py
- Class rename (planned): ToolRegistry → ToolHub (UnifiedToolManager semantics)
- Responsibilities:
  - Register tools with capability metadata (provider, modalities, cost tier)
  - Provide tool descriptors via progressive disclosure (basic → advanced)
  - Support tool chaining plans (sequential/parallel) and performance metrics tracking

No code rename executed yet; this is the approved plan pending your confirmation.

---

## 4) Model routing and escalation (GLM ↔ Kimi)

- First pass: glm-4.5-flash for speed/cost
- Escalation triggers: self-uncertainty, risk (security/auth/billing/migrations), coverage gaps, failures, cross-provider disagreement
- Second pass: glm-4.5 (quality) for code-heavy; optional Kimi cross-check for doc/long-context/vision
- For long-context or vision: prefer Kimi (moonshot) families

Implementation handle:
- Central ModelRouter making decisions per tool + constraints
- Respect per-tool defaults as in strategy doc; override by triggers

---

## 5) Context and token strategy

- Keep Phase 1 analysis with references only (no model calls)
- Final step: ≤10 essential files, strict token budgeting; truncate/skip large files without failure (already adjusted in BaseTool)
- Plan: chunking by section/function (follow-up) to include key regions of large files

---

## 6) Error handling and resilience

- Add ResilientErrorHandler with: retry policies, rate-limit handling, provider failover, clear user messages
- Standardize error categories and surface compact, actionable messages in tools

---

## 7) Security controls

- Implement SecureInputValidator for path/content guardrails in chat/analyze/multi-file tools
- Sanitize absolute paths (workspace-relative only), size caps, simple MIME checks

---

## 8) Migration plan (phased)

Phase A (now)
- [x] Expert analysis fallback shim (utils/expert_analysis_config.py)
- [x] Remove strict transport-size validation on internal file content (BaseTool)
- [ ] Add SecureInputValidator and wire to chat/analyze
- [ ] Create ModelRouter and wire to chat/analyze/codereview
- [ ] Prepare ToolHub class and adapter (no breaking rename yet)

Phase B
- [ ] Deprecate consensus internals; replace with workflow wrapper; add deprecation notice
- [ ] Collapse assessment-specific parsing into workflow mixin outputs
- [ ] Implement chunked file readers (by function/class/section)

Phase C
- [ ] Replace registry.py with tool_hub.py and rename references
- [ ] Introduce AutonomousWorkflowEngine for complex requests; consensus becomes a thin wrapper
- [ ] Add performance tracking + routing feedback loop (learning router, later)

---

## 9) Validation

- Unit tests: routing decisions, escalation triggers, secure input validation
- Simulator tests: quick mode + targeted codereview/analyze/precommit flows
- Logs: structured tool annotations (provider, model, file_count) for auditability

---

## 10) Developer ergonomics

- Keep tool names stable; deprecate rather than delete
- Short descriptions; advanced options behind flags
- Clear errors; link to docs for remediation steps

---

## 11) What still needs to be implemented (why)

- ModelRouter: unify routing; cost-aware and trigger-based (reduces spend, improves accuracy)
- ToolHub: registry rename and capability metadata (clarity, chain-aware orchestration)
- SecureInputValidator: security posture per prompts (path injection mitigation)
- Chunked readers: include critical parts of large files (effectiveness under token limits)
- ResilientErrorHandler: standardized resilient behavior (reliability)
- AutonomousWorkflowEngine: replace brittle legacy consensus/assessment flows (future-proofing)

