# Phase 2 – Updated Report (Pre-Batch 3)

Date: 2025-09-09
Scope: Confirm Batch 2 outcomes, lock routing policy, and prepare Batch 3 (providers → src/providers flip) with EXAI review gating.

Summary
- Routing: Think-deep auto-model selection is restriction-safe, prefers Kimi where allowed, and falls back to GLM “glm-4.5-flash”, then DEFAULT_MODEL from env.
- Restrictions: No use of restricted Kimi thinking aliases. Model discovery respects allow-lists without double filtering.
- Import direction: Tools/tests use src.providers.*; core server paths aligned.
- Readiness: Proceed to Batch 3 (flip shims) with EXAI MCP sweep and review.

Key Improvements since last report
1) Restriction-safe model routing
   - Kimi priority: kimi-k2-0905-preview → kimi-k2-0711-preview → moonshot-v1-{8k,32k}
   - GLM priority: glm-4.5-flash → glm-4.5 → glm-4.5-air
   - Final fallback: DEFAULT_MODEL from env when allowed
2) Registry hardening
   - Prevent double restriction filtering (provider filters respected; registry won’t refilter when already applied)
   - Health/circuit-breaker scaffolding present (env-gated)
   - Telemetry hooks for model usage (env-gated)
3) Provider consolidation (in progress)
   - src/providers now contains first-class implementations for: base, registry, kimi, glm
   - __init__.py exports registry, base types, and concrete providers
   - Remaining modules scheduled in Batch 3 flip: custom, openrouter, openrouter_registry, capabilities, metadata, openai_compatible (large)

Environment (excerpt)
- DEFAULT_MODEL=glm-4.5-flash
- KIMI_ALLOWED_MODELS and GLM_ALLOWED_MODELS present (consistent with policy)

Outstanding (non-blocking)
- Documentation/tests still mention legacy alias kimi-k2-thinking; will be updated after Batch 3 flip.

Next Steps
- Execute Phase 2 Batch 3 now: flip shims so src/providers is source of truth; legacy providers/* becomes thin shims to src/providers/*.
- Re-run EXAI MCP sweep and write Batch 3 sweep + review artifacts under this directory.
- Address any EXAI findings; then proceed to update docs/tests.



Post-Batch 3 confirmation (EXAI MCP)
- EXAI MCP tool: GREEN after fixes; sweep artifact: docs/sweep_reports/2025-09-09_11-50-41/mcp_tool_sweep_report.md
- src/providers/registry.py: added compatibility methods (list_available_models alias, get_available_providers_with_keys, get_preferred_fallback_model)
- Kimi/GLM now use utils/http_client for consistent HTTP calls
- .env loaded from repo root in registry to support all entrypoints

Next actions
- Cleanup docs/tests to remove legacy aliases (e.g., kimi-k2-thinking) and old import paths
- Optionally consolidate providers/openai_compatible.py into src/providers with providers.__init__ alias
