# EXAI MCP: Cost-Aware Model Routing and Expert Analysis Strategy

This document defines a practical, cost-conscious strategy for choosing when and how to use external models (GLM and Kimi), when to escalate model quality, and how to keep analysis effective without runaway costs. It aligns with the direction in:

- docs/external_review/auggie_cli_agentic_upgrade_prompt.md
- docs/external_review/auggie_cli_cleanup_prompt.md

and is designed for longevity and maintainability of the EX AI MCP Server.

---

## Executive summary

- Default to fast, low-cost models (glm-4.5-flash) for first-pass results.
- Escalate selectively based on uncertainty or risk signals, not by default.
- Prefer GLM for code-heavy analysis/review; Kimi (Moonshot) is strong too—use it for cross-checks and multimodal/vision or long context needs.
- Keep expert analysis off by default. Turn it on only in final steps with a small, essential file set and explicit cost warnings.

---

## Model pool and strengths (current providers)

- GLM
  - glm-4.5-flash: low cost, fast; great for first-pass reviews and routing decisions
  - glm-4.5 (quality): higher accuracy on code understanding/reasoning; use for targeted second-pass validation
- Kimi / Moonshot
  - kimi-k2(-turbo/-preview): fast, reliable, OpenAI-compatible; good for general chat and cross-checks
  - moonshot-v1-* (8k/32k/128k, vision variants): larger context, vision; good for doc-heavy or image-involved tasks

Guideline: favor GLM for code review/refactor/debug; use Kimi for cross-validation, rich text synthesis, vision, or where its behavior has proved strong in project tests.

---

## Routing policy by tool

- chat: glm-4.5-flash (fallback to kimi-k2-turbo if user prefers). Escalate only if user explicitly requests deep reasoning.
- analyze (workflow): Phase 1 local-only (no model) + references. Optional Phase 2 expert pass with glm-4.5-flash; escalate to glm-4.5 if high-risk or low-confidence.
- codereview: glm-4.5-flash → escalate to glm-4.5 when changes touch core code paths or tests fail. Optional cross-check with Kimi on key diffs.
- debug: glm-4.5-flash; escalate if multi-module root cause suspected (signals: repeated failures, flaky tests). Cross-check with Kimi for alternate hypothesis.
- refactor: glm-4.5-flash; escalate for decomposition planning across large modules. Use Kimi to compare two alternative refactor plans.
- secaudit: glm-4.5 (quality) directly for critical audits, or glm-4.5-flash for quick triage. Avoid Kimi unless multimodal context or long-doc review is required.
- testgen: glm-4.5-flash; escalate if complex stateful interactions or concurrency detected (heuristic: fixtures + asyncio/threads + IO boundaries).
- planner: local logic (no model) by default; if model is used, flash tier suffices.
- precommit: local analysis and minimal model usage (flash). Escalate only for risky diffs (migration, auth, payment paths).
- tracer/thinkdeep/consensus/docgen: flash first; escalate only if explicit user need or confidence is low.

---

## Escalation triggers (from cheapest → better)

Use one or more triggers to justify the next tier or cross-provider validation:

1) Self-uncertainty
- Model produces low-confidence phrasing ("not sure", "may", "unclear") or contradicts itself
- Sparse or generic rationale without concrete references

2) Risk classification
- Changes touch security, auth, billing, migrations, or external integrations
- Tool = secaudit; or testgen for high-stakes modules

3) Coverage gap
- Significant files excluded (due to size) that are essential to the question
- Diff coverage < 70% of impacted modules

4) Failure signals
- Unit tests fail; or precommit checks flag risks
- Repeated debug attempts without progress

5) Cross-provider disagreement
- GLM and Kimi disagree materially → keep a short cross-check loop and reconcile

---

## Cost controls (defaults and practice)

- DEFAULT_USE_ASSISTANT_MODEL=false (already recommended)
- EXPERT_ANALYSIS_MODE=auto with warnings and cost summaries on
- Final-step expert analysis only, with ≤10 essential files
- Use glm-4.5-flash by default; escalate to glm-4.5 only if triggers fire
- Truncate/skipping large files instead of failing (implemented in BaseTool fix)
- File prioritization: core orchestrators, provider adapters, tool registry, base_tool, workflow mixin, utils

---

## File handling strategy

- Phase 1: references only (no embedding) to map architecture and scope cheaply
- Phase 2: embed small essential subset; skip large monolithic reports or break them into targeted sections if needed (future: chunking)
- Maintain conversation-aware deduplication; allow token optimization to trim excess

---

## Implementation plan (what still needs to be implemented and why)

Short-term (now/next PRs)
- [ ] ModelRouter decision utility
  - Why: centralize routing logic (tool type, risk, confidence → model)
  - Inputs: tool name, risk score, self-uncertainty heuristics, file scope size
  - Output: model name and optional cross-check plan
- [ ] Confidence/uncertainty heuristic
  - Why: trigger escalation when first-pass answer looks weak
  - Approach: regex/keyword score on response rationale; optional logit bias from provider if available
- [ ] Cost estimator per call
  - Why: show user explicit cost estimates and thresholds prior to escalation
  - Inputs: token allocation, number of files, model pricing table
- [ ] Minimal cross-check flow
  - Why: detect disagreements between GLM and Kimi on critical findings
  - Approach: second model quick-pass on the same prompt; reconcile summary

Near-term
- [ ] Chunked file reading (targeted sections)
  - Why: include key regions of large files rather than skip entire files
  - Approach: section markers or code-aware chunking (classes/functions)
- [ ] Risk classifier
  - Why: prioritize audits for auth/security/payments; gate escalation
  - Approach: path patterns (auth, payment, secrets), keywords, diff heatmap
- [ ] Per-tool routing defaults codified
  - Why: consistent behavior; match guidelines above per tool
- [ ] CI/config toggles
  - Why: allow project-wide profile: "speed", "balanced", "quality"

Mid-term
- [ ] Learning-based router
  - Why: improve decisions over time using feedback signals (user accept/revert, test outcomes)
- [ ] Provider capability cache and health scoring
  - Why: adapt to provider outages and performance fluctuations
- [ ] Detailed cost dashboards and monthly budgets
  - Why: manage spend proactively

---

## Operational guardrails

- Keep expert analysis opt-in per final step; don’t call external models during intermediate steps
- Always show pre-check warnings for cost and privacy when expert analysis is enabled
- Ensure logs mark model, provider, and file counts for observability

---

## Alignment with Auggie CLI prompts

- Agentic upgrade prompt: architect multi-phase rollout; this strategy supplies concrete model routing and cost gating to those phases
- Cleanup prompt: reduce legacy/broken systems and centralize control → ModelRouter unifies routing; file handling simplification and token budgeting align with complexity reduction

---

## Next actions

- Approve this strategy
- Implement ModelRouter + uncertainty heuristic + minimal cross-check (short-term items)
- Wire Chat/Analyze/CodeReview/Debug/SecAudit/TestGen to use ModelRouter decisions
- Add unit tests for routing logic and escalation triggers

