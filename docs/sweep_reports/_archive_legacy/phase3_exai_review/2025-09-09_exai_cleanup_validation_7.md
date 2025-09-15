# Phase 7 — Consolidation + resiliency: GLM base host, PID mutex, token estimates

Date: 2025-09-09

## Scope
- Consolidate GLM base host (prefer api.z.ai) and simplify env
- Add PID-file mutex in wrapper to prevent duplicate EXAI server instances
- Improve token estimation heuristics (CJK-aware) for GLM and Kimi

## Changes implemented

1) GLM base host consolidation
- src/providers/glm.py
  - DEFAULT_BASE_URL now uses `os.getenv("GLM_API_URL", "https://api.z.ai/api/paas/v4")`
- .env
  - GLM_API_URL switched to https://api.z.ai/api/paas/v4
  - GLM_AGENT_API_URL deprecated/commented in favor of GLM_API_URL

2) Single-instance PID mutex
- scripts/mcp_server_wrapper.py
  - Creates logs/exai_server.pid on startup; refuses to start if a recent lock exists
  - Stale lock handling via EXAI_LOCK_STALE_SECONDS (default 900s)
  - EXAI_LOCK_DISABLE=true allows bypass (for development)
  - Lock is deleted on normal exit (atexit)

3) Token estimation improvements (CJK-aware)
- src/providers/glm.py and src/providers/kimi.py
  - Detects CJK ratio; if > 0.2, estimate ≈ 0.6 tokens/char
  - Else ≈ 4 chars/token heuristic
  - Fallback to previous approach on any exception

## Outcome
- Operational
  - Reduced chance of red/disconnected state after toggle by avoiding double-launch (mutex)
  - Clearer, centralized GLM base host; fewer surprises across environments
- Functional
  - More realistic token estimates for Chinese/Japanese/Korean text

## Notes
- We kept `.env` as the single source of truth for GLM_API_URL; code default is api.z.ai.
- If your deployment requires bigmodel.cn, set GLM_API_URL accordingly.
- PID mutex is intentionally conservative; use EXAI_LOCK_DISABLE=true for dev override.

## Next steps (optional)
- Add retry/backoff around multipart uploads in HttpClient
- Introduce FileService to centralize file validations (size/mime/checksum)
- Add smoke tests for uploads and token metrics in CI

