# Tools registry guard — core set + allowlist (gated)

One-liner: YES — Implemented env-gated registry filter; requires server restart to take effect.

## What changed
- Added TOOLS_CORE_ONLY and TOOLS_ALLOWLIST gates inside tools/registry.py build_tools()
- Core set (when TOOLS_CORE_ONLY=true):
  chat, analyze, codereview, debug, precommit, refactor, secaudit, testgen, thinkdeep, tracer, activity, health
- Allowlist (TOOLS_ALLOWLIST=comma,list) augments/overrides the active set
- Backward-compatible defaults: gates are OFF by default (no behavior change until enabled)

## How to enable (after restart)
- TOOLS_CORE_ONLY=true → restrict to core set (plus allowlist)
- TOOLS_ALLOWLIST=chat,activity → show only these (or expand core when core-only)

## Validation plan (post-restart)
- After server restart, refresh Augment settings/extension
- Use EXAI-WS activity to confirm list_tools()/descriptors reflect gated set
- Record excerpts under docs/augment_reports/augment_review_02/


## Update (2025-09-24)
- Core set expanded to include diagnostics: version, listmodels
- Reason: keep discovery/health visibility when TOOLS_CORE_ONLY=true without requiring allowlist
- Gating remains OFF; final flip will be bundled with a single Augment restart at the end of Batch B
