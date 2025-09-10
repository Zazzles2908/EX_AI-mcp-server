# Phase 2 – Batch 3 EXAI Review (Providers → src/providers flip)

Date: 2025-09-09
Sweep report: docs/sweep_reports/2025-09-09_11-50-41/mcp_tool_sweep_report.md

Summary
- Source-of-truth is now src/providers for: base, registry, kimi, glm, custom, openrouter, openrouter_registry, capabilities, metadata.
- Backward compatibility retained: providers/__init__.py aliases legacy imports to src.providers.* (e.g., providers.custom → src.providers.custom).
- Routing policy: restriction-safe; prefers Kimi when allowed; GLM prefers glm-4.5-flash; final fallback uses DEFAULT_MODEL from .env when allowed.
- MCP tool status: GREEN. Runtime fixed by re-pointing imports and adding utils/http_client.

Validation (EXAI MCP sweep)
- Server initialized; tools discovered (analyze, challenge, chat, consensus, listmodels, orchestrate_auto, thinkdeep, version).
- Provider registry exports match server usage (register_provider, get_available_models, list_available_models alias, get_available_providers_with_keys, get_preferred_fallback_model).
- .env read from repository root by registry; no spurious warnings.

Key changes in Batch 3 (post-fix)
1) Compatibility methods restored in src/providers/registry.py
   - Added: list_available_models (alias), get_available_providers_with_keys, get_preferred_fallback_model.
   - Ensures server diagnostics and selection helpers work.
2) Shared HTTP client introduced
   - New: utils/http_client.py; Kimi/GLM use this for simple JSON POST/GET with API key headers.
3) Env-loading correction
   - Registry now loads .env from repo root rather than src/.env.
4) OpenAI-compatible path
   - src/providers/custom.py and src/providers/openrouter.py import OpenAICompatibleProvider from providers.openai_compatible (legacy file kept).

Risks / follow-ups
- providers/openai_compatible.py remains under legacy package; can migrate later for full src/ consolidation.
- Docs/tests still mention legacy aliases (e.g., kimi-k2-thinking) and paths; safe to update next.

Recommendation
- Proceed with documentation and test reference cleanup.
- Optional: Move providers/openai_compatible.py → src/providers/openai_compatible.py and add alias in providers/__init__.py.

Artifacts
- Sweep: docs/sweep_reports/2025-09-09_11-50-41/mcp_tool_sweep_report.md
- Phase report: docs/sweep_reports/phase2_exai_review/phase2_updated_report.md
