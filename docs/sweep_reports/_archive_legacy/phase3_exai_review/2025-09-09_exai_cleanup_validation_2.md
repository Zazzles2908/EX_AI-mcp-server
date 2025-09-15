## Phase 3 (v2) — SDK audit for Moonshot (Kimi) and ZhipuAI (GLM)

### Scope
Requested follow-up focusing on native SDK usage vs OpenAI-compatible flows, using EXAI to audit code paths and recent behavior, then documenting actions and next recommendations.

### What EXAI found (code-level evidence)
- Kimi/Moonshot
  - src/providers/kimi.py extends an OpenAI-compatible base; no native Moonshot SDK import detected.
  - Legacy providers/kimi.py also uses the OpenAI-compatible path (including files.create via the client), i.e., not native.
  - Base URL variance observed: defaults point to https://api.moonshot.cn/v1 while logs show calls to https://api.moonshot.ai/v1. This is configurable via KIMI_API_URL and should be unified per region/account.
  - Tools (tools/kimi_upload.py, tools/kimi_tools_chat.py) call provider.client.chat.completions.create — still through OpenAI-compatible client.

- GLM/ZhipuAI
  - src/providers/glm.py tries to import and use the official zhipuai SDK (ZhipuAI), falling back to a pure HTTP client (PaaS v4 /chat/completions) when unavailable.
  - Legacy providers/glm.py uses OpenAI-compatible base with an optional zhipu_optional loader.
  - Conclusion: We already support native SDK for GLM optionally in the new path; there is duplication (legacy vs src) to consolidate.

- OpenAI-compatible base
  - src/providers/openai_compatible.py is currently a shim re-exporting providers/openai_compatible.py. The real implementation (providers/openai_compatible.py) contains robust response parsing, streaming support, and usage extraction.

### Current behavior (runtime checks)
- Kimi and GLM are healthy: EXAI listmodels/version OK; recent logs show successful Moonshot calls (HTTP 200) and valid completions.
- ThinkDeep and Analyze: validation/size guardrails function correctly; errors observed were input/schema related, not provider failures.

### Recommendations and plan (SDK-focused)
1) Kimi/Moonshot
   - Continue using OpenAI-compatible flow as the primary path (stable).
   - Add optional native SDK hook if/when Moonshot provides an official Python SDK we can depend on (mirror the GLM pattern: try import, else fallback). Note: install requires user approval per policy.
   - Normalize KIMI base URL by env (KIMI_API_URL) and document .ai vs .cn; prefer a single default, overridable via env.

2) GLM/ZhipuAI
   - Consolidate to src/providers/glm.py as the canonical provider (keeps optional native SDK usage). Deprecate legacy providers/glm.py once all imports updated.

3) Eliminate cross-tree shim
   - Move providers/openai_compatible.py implementation into src/providers/openai_compatible.py and update imports in src providers, then retire the legacy module. This reduces confusion and duplication.

4) Tool coupling reduction
   - Prefer provider.generate_content in tools rather than reaching into provider.client directly. Where provider-specific file APIs are needed, add wrapper methods on the provider to keep the interface consistent.

### Immediate actions taken (v2)
- Completed EXAI analyze-based audit of SDK usage across providers and related tools, and verified runtime health in logs.
- Captured explicit consolidation plan above; no code changes were applied in this v2 pass to avoid risk during your current session. I can implement the consolidation next as Phase 4 upon confirmation.

### Proposed Phase 4 tasks (ready to execute)
- Implement src/providers/openai_compatible.py with the current robust implementation and update src providers to import from src.* exclusively.
- Update references to use src/providers/glm.py; mark legacy providers/glm.py for deprecation; keep zhipu_optional only if still useful.
- Add optional native Kimi hook (guarded import) when an official SDK package/name is confirmed; keep OpenAI-compatible as default.
- Adjust KIMI_API_URL default to your preferred domain (.ai or .cn) and document.
- Reduce direct client calls in tools: migrate to provider.generate_content and add provider wrappers for files API.

### Acceptance checks post-Phase 4
- listmodels/version: unchanged (OK)
- chat/thinkdeep: pass on Kimi + GLM models
- tools using files API (Kimi upload/extract): pass using provider wrappers
- no shim imports from providers.* used by src/* code paths

If you approve, I will begin Phase 4 and then produce v3 report with pass/fail matrix and latency/usage summary.
