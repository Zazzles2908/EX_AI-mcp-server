# Phase 1 – Provider Status (Kimi)

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Summary
- Allowed providers: KIMI, GLM (.env ALLOWED_PROVIDERS=KIMI,GLM)
- Defaults: GLM_FLASH_MODEL=glm-4.5-flash, GLM_QUALITY_MODEL=glm-4.5, KIMI_DEFAULT_MODEL=kimi-k2-0711-preview, KIMI_SPEED_MODEL=kimi-k2-0711-preview
- Routing: ROUTER_ENABLED=true, EX_ROUTING_PROFILE=balanced, WORKFLOWS_PREFER_KIMI=true
- Daemon limits: EXAI_WS_KIMI_MAX_INFLIGHT=10, EXAI_WS_GLM_MAX_INFLIGHT=10 (global 48)
- Compatibility: EXAI_WS_COMPAT_TEXT=true; EXPERT_MICROSTEP=true (analyze heartbeat/timeouts set)

Environment keys (present/non-empty)
- KIMI_API_KEY: present
- GLM_API_KEY: present; GLM_API_URL=https://open.bigmodel.cn/api/paas/v4

Model selections and fallbacks
- Kimi fallback order: KIMI_FALLBACK_ORDER=kimi-k2-0905-preview,kimi-k2-0711-preview
- Expensive thinking fallback disabled (KIMI_ALLOW_EXPENSIVE_THINKING_FALLBACK=false)

Provider modules detected
- tools/providers/kimi: kimi_tools_chat.py, kimi_upload.py, kimi_embeddings.py, kimi_files_cleanup.py
- tools/providers/glm: glm_agents.py, glm_files.py, glm_files_cleanup.py
- src/providers: kimi.py, glm.py, registry.py, base.py, metadata.py, capabilities.py, openrouter.py (optional), openai_compatible.py (optional), zhipu_optional.py

Risks & notes
- Ensure model IDs match current provider catalogs (no deprecated IDs)
- Respect inflight limits during batch workflows to avoid throttling
- Keep ROUTER_PREFLIGHT_CHAT=false to avoid background cost unless explicitly enabled

Next actions
1) Validate live model availability via listmodels/provider_capabilities
2) Run provider-safe diagnostics (tools/diagnostics/health.py, status.py) and capture outputs
3) Ensure retries/backoff in provider tools reflect RESILIENT_RETRIES/RESILIENT_BACKOFF_SECS
4) Confirm tool_choice safeguards in Kimi chat with tools path

This section will be replaced by the authoritative Kimi analysis output once received.
