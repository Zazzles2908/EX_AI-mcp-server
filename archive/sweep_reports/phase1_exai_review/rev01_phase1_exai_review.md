# Phase 1 – EXAI Review (rev01)

This file captures the EXAI MCP codereview findings and actionable steps applied to complete Phase 1.

## Findings Summary

- Documentation neutrality achieved for key tool pages (analyze, debug, refactor, secaudit) and config comments.
- Server behavior made client‑agnostic using CLIENT_* env with CLAUDE_* fallback (allow/deny lists, websearch default, thinking mode, workflow cap).
- Schemas now display canonical model names (aliases/snapshots filtered).
- Sweep report includes provider_used/model_used and durations; workflow tools complete step 1.
- Residual docs/scripts refer to Claude (CLAUDE.md, README-ORIGINAL.md, run-server.*) – to be addressed in reorg phase.
- .env allowed model lists were noisy (snapshots/aliases/provider ids).

## Actions Implemented (this revision)

- Pruned production .env allowlists to canonical sets:
  - KIMI_ALLOWED_MODELS=kimi-latest-8k,kimi-latest-32k,kimi-latest-128k,moonshot-v1-auto
  - GLM_ALLOWED_MODELS=glm-4,glm-4-plus,glm-4-air,glm-4.5,glm-4.5-air,glm-4.5-flash
- Kept CLAUDE_* env values for backward compatibility while enabling CLIENT_* profiles.
- Left CLAUDE.md/README-ORIGINAL.md/run-server.* for Phase 2 documentation reorganization (non-blocking).

## Validation

- EXAI sweep previously confirmed canonical models in schemas and printed Resolved: provider/model metadata with durations.
- Phase 1 acceptance criteria met for reviewed scope.

## Next Steps

- Proceed with Phase 2 planning (file move map, shims), then reorg docs (move CLAUDE.md to guides, neutralize run-server messaging).
