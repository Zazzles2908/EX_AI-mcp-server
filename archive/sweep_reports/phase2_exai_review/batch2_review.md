# Phase 2 – Batch 2 EXAI Review (post-fix)

Scope: Providers import migration to src.providers.*, thinkdeep auto-model routing made restriction-safe, supplemental tool fixes.

Key changes
- server.py: ThinkDeep auto-model now selects from allowed Kimi models by priority (kimi-k2-0905-preview, kimi-k2-0711-preview, kimi-k2-0905, moonshot-v1-128k/32k/8k/auto) using ModelProviderRegistry.get_available_models(respect_restrictions=True). GLM fallback remains glm-4.5.
- tools/recommend.py: Migrated to src.providers.registry import and replaced kimi-k2-thinking with kimi-k2-0905-preview in EXTENDED_REASONING candidates.
- tools/kimi_tools_chat.py: Migrated provider imports to src.providers.*.
- src/providers/__init__.py: Ensures ModelProviderRegistry re-export so `from src.providers import ModelProviderRegistry` works.

Sweep status
- Server initializes; providers detected (KIMI, GLM).
- Tools discovered: analyze, challenge, chat, consensus, listmodels, orchestrate_auto, thinkdeep, version.
- No restriction violations observed in auto-routing logic after fix.

Risks & notes
- Docs and simulator tests still reference 'kimi-k2-thinking' (non-blocking for runtime).
- In Batch 3, after moving providers/ -> src/providers/, update docs/tests to reflect new model guidance and imports.

Verdict
- Batch 2 import migration and routing fix look good. Ready to proceed to Batch 3 (actual file moves) after your review.

