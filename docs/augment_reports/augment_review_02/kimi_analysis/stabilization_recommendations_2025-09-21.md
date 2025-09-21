# Phase 1 – Stabilization Recommendations (Kimi)

Status: IN PROGRESS (autonomous fill; will be overwritten by Kimi Step 2 output on arrival)
Date: 2025-09-21

Prioritized fixes
1) WS bridge:
   - Alias normalization (applied)
   - Non-empty-first payload guard (applied)
2) Registry/schema:
   - Verify TOOL_MAP import paths for all workflow tools
   - Ensure get_descriptor() implemented/robust across tools
   - Align schemas/timeouts across workflows (WORKFLOW_STEP_TIMEOUT_SECS, ANALYZE_* env)
3) Providers:
   - Validate Kimi/GLM model IDs live; keep fallbacks; ensure retries/backoff
   - Guard tool_choice usage in Kimi tools; verify upload/cleanup flows
4) Router:
   - Implement manager-first routing (Phase 3): request classification, tool delegation, provider orchestration

Validation plan (Phase 4)
- Smoke: chat/analyze unpredictable prompts; listmodels parity
- Diagnostics: health/status/provider_capabilities; router checks with route_diagnostics
- Folder-specific tool invocations (minimal) to confirm schemas & timeouts

Risks & mitigations
- Empty payload regressions → WS guard remains enabled; log diagnostics
- Rate limiting during batch analyses → respect inflight limits; stagger calls

This section will be replaced by the authoritative Kimi analysis output once received.
