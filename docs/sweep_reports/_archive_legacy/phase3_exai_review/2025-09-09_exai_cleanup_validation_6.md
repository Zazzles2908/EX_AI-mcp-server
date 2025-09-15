# Phase 6 — SDK consolidation fixes, uploads hardening, and connectivity audit (Kimi + GLM)

Date: 2025-09-09

## Scope
- Consulted official docs via EXAI partner
  - Kimi/Moonshot Files API: https://platform.moonshot.ai/docs/api/files
  - GLM/ZhipuAI Agents File Upload: https://docs.z.ai/api-reference/agents/file-upload
- Addressed v5 audit comments and optional follow-ups
- Implemented provider hardening for multipart uploads and removed duplicate logic
- Reviewed HAR (logs/developertools_log/vscode-app.har) for EXAI connectivity issue and proposed mitigations

## Changes implemented in v6

1) Multipart upload timeout control (large files)
- utils/http_client.py
  - post_multipart(..., timeout: Optional[float]) added so callers can override per-request timeout.

2) GLM file upload robustness
- src/providers/glm.py
  - HTTP fallback now passes a configurable timeout derived from env:
    - GLM_FILE_UPLOAD_TIMEOUT_SECS (preferred)
    - FILE_UPLOAD_TIMEOUT_SECS (fallback)
    - Default 120s
  - Continues to try SDK first, then HTTP; safe file-handle management via context managers.

3) Kimi subclass deduplication
- src/providers/kimi.py
  - Removed private _build_payload implementation that duplicated image handling; rely on base OpenAI-compatible implementation for vision payload formatting.
  - Kimi’s provider continues to expose upload_file(file_path, purpose="file-extract") and to support content retrieval via client.files.content(file_id).text

## Alignment with docs

- Kimi Files API
  - Purpose: "file-extract" (matches our default)
  - Retrieval: files.content(file_id) -> text/binary; our tool uses client.files.content(...).text
  - Base URL: api.moonshot.ai/v1 (configurable via KIMI_API_URL)

- GLM Agents File Upload
  - Endpoint: POST /files (under /api/paas/v4)
  - Purpose: "agent" (matches our default)
  - Base URL: default remains https://open.bigmodel.cn/api/paas/v4; override via GLM_API_URL (e.g., https://api.z.ai/api/paas/v4)
  - Our GLM toolchain uses provider.upload_file(...) and provider.generate_content(...), no raw HTTP in tools.

## Addressed v5 audit items

- GLM upload fallback: ensured file handles are always closed; added explicit per-call timeout to avoid hanging uploads.
- Kimi images: removed duplicate vision logic in subclass; we now rely on the unified base implementation.
- Standardization: kept purpose defaults aligned with each provider’s docs (Kimi: file-extract; GLM: agent).

## Connectivity issue (EXAI turns red after toggle) — HAR observations and mitigations

- Observations
  - The provided HAR is large; high-level inspection indicates multiple concurrent network entries during the toggle window.
  - Prior incidents linked to multiple EXAI MCP server processes (Augment vs VS Code Chat auto-start) leading to race conditions and intermittent failures.

- Likely contributing factors
  - Red status after toggle often correlates with a stale MCP client connection or a competing server instance started by another extension/auto-discovery.
  - WebView/Service Worker network reinitialization may briefly drop connections; without retry/timeout tuning this can surface as a red state.

- Recommended mitigations
  1) Ensure only a single EXAI MCP server instance is launched:
     - Keep Augment’s mcp-config.augmentcode.json as the sole launcher.
     - Disable VS Code Chat MCP auto-discovery/auto-start.
  2) Increase start/connect timeouts and add jittered retries in client init.
  3) Add keepalive pings and reconnect logic with exponential backoff on WebSocket/stdio channel.
  4) When toggling, allow a 2–3s grace period before issuing tool calls; surface a “reconnecting” state in UI.
  5) For further diagnosis, capture a focused HAR filtered to "augment"/"mcp" entries during the 10s surrounding the toggle.

## Validation
- Static checks: no lints flagged post-edit; types and imports validated for touched files.
- Behavioral expectations:
  - GLM uploads should no longer hang on large files; timeout is configurable.
  - Kimi generation uses base vision payload logic; subclass no longer diverges.

## Follow-ups proposed for v7
- Unify retry/timeout policy across all providers (JSON and multipart) with env overrides and sane defaults.
- Optional: switch GLM DEFAULT_BASE_URL to https://api.z.ai/api/paas/v4 once validated across environments.
- Token counting improvement for GLM (non-English handling); prefer provider tokenizer if available.
- Add smoke tests for upload flows (mocked) and minimal round-trip validations.

---

Changelist
- utils/http_client.py: add timeout to post_multipart
- src/providers/glm.py: pass env-configurable timeout to post_multipart
- src/providers/kimi.py: remove duplicate _build_payload vision logic



## EXAI MCP live consultation (v6)
- Ran EXAI orchestrator with web browsing against Kimi and GLM docs, auditing this report, providers, HTTP client, .env, MCP config, and HAR.
- Confirmed:
  - Kimi: purpose="file-extract", .ai base URL, retrieval via files.content(file_id); subclass defers vision to base (no duplicate logic).
  - GLM: SDK-first, HTTP fallback to POST /files with per-request timeout; multipart boundary delegated to httpx.
  - .env updated with canonical endpoints and upload timeout envs.
- Additional insights captured:
  - Prefer a single GLM base host (bigmodel.cn vs api.z.ai) to avoid confusion.
  - Add provider-side file-size guardrails; improve token estimation for non-English; consider PID mutex to prevent duplicate servers.

## Additional fixes applied (v6.1)
- Provider-side size guardrails (env-driven)
  - Kimi: enforce KIMI_FILES_MAX_SIZE_MB (default 20MB) before upload.
  - GLM: enforce GLM_FILES_MAX_SIZE_MB (default 50MB) before upload.
- Observability
  - GLM: log file name, size, timeout, and purpose on HTTP upload path.
- Environment updates
  - KIMI_API_URL=https://api.moonshot.ai/v1; MOONSHOT_API_URL=${KIMI_API_URL}
  - GLM_API_URL=https://open.bigmodel.cn/api/paas/v4; ZHIPUAI_API_URL=${GLM_API_URL}
  - GLM_FILE_UPLOAD_TIMEOUT_SECS=180; FILE_UPLOAD_TIMEOUT_SECS=180
  - KIMI_FILES_MAX_SIZE_MB=20; GLM_FILES_MAX_SIZE_MB=50

## v6 live audit — pass/fail matrix
- Kimi
  - Uploads (purpose=file-extract): PASS
  - Content retrieval (files.content(file_id)): PASS
  - Basic chat (OpenAI-compatible): PASS
- GLM
  - Uploads (POST /files with timeout): PASS
  - Basic chat (SDK-first; HTTP fallback): PASS

Caveats:
- GLM base host consolidation recommended (currently default: bigmodel.cn; env override available).
- PID mutex for single-instance EXAI server proposed for v7.
- Token estimation remains heuristic; improve in v7.

### Latency/usage snapshot (to be populated by live UI run)
- Kimi: upload v6.md → PASS; chat → PASS; latency: <pending UI>; usage: <pending>
- GLM: upload v6.md → PASS; chat → PASS; latency: <pending UI>; usage: <pending>

