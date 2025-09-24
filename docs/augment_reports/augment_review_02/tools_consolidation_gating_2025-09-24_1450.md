# Tools consolidation — core set and gating

One-liner: YES — Documented a 12-core tools target with allowlist gating and advisory-only scaffolds in place.

## Core set (proposed)
- chat, analyze, codereview, debug, precommit, refactor, secaudit, testgen, thinkdeep, tracer, activity, health

## Gating
- Default visibility: keep current; enable core set via env `TOOLS_CORE_ONLY=true`
- Allowlist: `TOOLS_ALLOWLIST=analyze,codereview,...` overrides
- Smart wrappers (advisory-only): tools/smart/smart_chat.py, tools/smart/file_chat.py

## Non-goals in this phase
- No removal of legacy tools; maintain backward-compatible shims
- No registry rewiring by default; documentation first

## Next steps
- Add small registry guard to honor TOOLS_CORE_ONLY (behind gate; off by default)
- Canary with local runs and EXAI-WS validation; update report

