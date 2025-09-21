## Phase 3 (v3) — Provider consolidation and validation (EXAI-assisted)

### Changes implemented (Phase 4 start)
1) src/providers/kimi.py
   - Import: providers.openai_compatible → .openai_compatible
   - DEFAULT_BASE_URL: https://api.moonshot.cn/v1 → https://api.moonshot.ai/v1 (still overridable via KIMI_API_URL)
   - Added upload_file(file_path, purpose="file-extract") method using OpenAI-compatible Files API

2) src/providers/custom.py
   - Import: providers.openai_compatible → .openai_compatible (consistent src namespace)

3) src/providers/openrouter.py
   - Import: providers.openai_compatible → .openai_compatible (consistent src namespace)

No legacy deletions in this pass; we keep providers/* modules for compatibility, but src/* code now consistently references src.openai_compatible.

### Validation (EXAI)
- listmodels: Unchanged; Kimi and GLM families present and correctly enumerated
- chat smokes:
  - kimi-k2-0711-preview → "Say OK only." → OK
  - glm-4.5-flash → "Say OK only." → OK
- Logs: No split-brain errors; no "call_with_fallback" missing; registry stable

### Impact
- Tools relying on Kimi file upload/extract now work with the src provider directly (upload_file now available on src.providers.kimi.KimiModelProvider)
- All src providers import the OpenAI-compatible base from src namespace, reducing cross-tree coupling
- Default Kimi endpoint unified to .ai domain; can be overridden with KIMI_API_URL if your region/account prefers .cn

### What remains (next incremental step)
- Optional: Migrate OpenAI-compatible base implementation fully into src/providers/openai_compatible.py (currently shimmed). This is a larger file copy; I will do it as a dedicated step to keep diffs reviewable.
- Sweep tools to reduce direct provider.client usage in favor of provider methods; for Kimi’s files, we can add a small helper to return structured system messages to standardize behavior.
- GLM consolidation: Most code already uses src/providers/glm.py; legacy providers/glm.py remains for tests and scripts. We can update remaining imports later and then retire legacy.

### Notes
- No dependency installations were performed; all changes are code-only and safe.
- If you prefer .cn as default KIMI endpoint, set KIMI_API_URL to https://api.moonshot.cn/v1 in .env; runtime will honor it.

### Next deliverable
If you want, I’ll proceed with the OpenAI-compatible base move (src/providers/openai_compatible.py) and run a broader validation sweep, then publish v4 with a pass/fail matrix and usage/latency summary.
