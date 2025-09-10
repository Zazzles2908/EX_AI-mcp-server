## FileCache for Upload Deduplication (EX-AI-MCP-Server)

This document describes the FileCache system used to avoid redundant file uploads across providers (Kimi, GLM).

### Overview
- Cache key: SHA256 of file contents
- Value: Per-provider mapping to `{file_id, ts}`
- Persistence: JSON file on disk
- Expiration: TTL (seconds) per entry
- Integration: Checked by upload tools before calling provider; on hit, reuse `file_id` and skip upload
- Observability: JSONL metrics emit cache `hit`/`miss` events and upload `file_count_delta` on new uploads

### Environment Variables
- `FILECACHE_ENABLED` (default: `true`)
  - Gate to enable/disable cache checks and updates in tools
- `FILECACHE_PATH` (default: `.cache/filecache.json`)
  - Path to the JSON persistence file; directories are created as needed
- `FILECACHE_TTL_SECS` (default: `604800` == 7 days)
  - TTL for cached entries. `0` disables expiration.
- `EX_METRICS_LOG_PATH` (optional; default: `.logs/metrics.jsonl`)
  - Observability sink used for cache metrics and upload counters

### Behavior
1. On upload request:
   - Compute SHA256 of file
   - If `FILECACHE_ENABLED` is true, check cache for provider key (e.g., `KIMI`/`GLM`)
   - If present and not expired: record `file_cache:hit` and reuse `file_id`
   - If absent/expired: record `file_cache:miss`, perform provider upload, then write `{file_id, ts}` back to cache and record `file_count_delta:+1`
2. On read:
   - Expired entries are pruned lazily at access time
3. Persistence:
   - Cache is read on init and written on each set; failures are swallowed (best-effort)

### Observability Events
- `{"event":"file_cache","action":"hit|miss","provider":"KIMI|GLM","sha":"..."}`
- `{"event":"file_count_delta","provider":"KIMI|GLM","delta":+1}`

### Expected Performance Impact
- Eliminates repeated uploads of identical files across sessions/process restarts
- Savings scale with repeated usage; typical reductions of 50–90% in dev workflows where files are retried or shared across tools
- JSON persistence overhead is minimal relative to provider upload costs

### Notes
- Cache is content-addressed: any change to file contents yields a new SHA and new upload
- For very large caches, consider external stores (SQLite/Redis) in the future; current JSON approach is intentionally simple
- Windows paths are normalized via `Path` APIs; no platform-specific logic required

