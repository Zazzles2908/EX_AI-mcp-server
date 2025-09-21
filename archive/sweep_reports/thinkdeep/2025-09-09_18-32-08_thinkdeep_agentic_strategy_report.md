# EXAI Agentic, Cost-Aware Methodology (Thinkdeep v1)

Date: 2025-09-09
Run: f5649ac6-3e1a-4ec3-9354-bf4f07c5f6fa
Artifacts: see raw run JSON alongside this file

## Executive Summary
- Objective: Craft an agentic methodology for EXAI that balances cost, latency, and quality across Kimi and GLM, using uploads, browsing, and routing smartly.
- Outcome: A practical playbook with routing heuristics, upload/caching policy, browsing gates, and configuration knobs. Ready to implement incrementally (Phases v8+).

## Provider Constraints (doc-grounded)
- Kimi/Moonshot Files API
  - Purpose: file-extract; content retrieval via files.content(file_id)
  - Vision: images supported on specific models; prefer base payload for multimodal
  - Practical: keep files under ~20MB; cache file_id for reuse when stable
- GLM/ZhipuAI Agents File Upload
  - Endpoint: POST /files under /api/paas/v4; purpose: agent
  - SDK-first usage with HTTP fallback; prefer single canonical base host (api.z.ai)
  - Practical: files ≤ ~50MB advisable; pass per-request timeouts; cache file_id when appropriate

## Routing Strategy (token/cost-aware)
- Default routing policy
  - Single Q&A (non-vision, < 3k tokens est): glm-4.5-flash (fast, economical)
  - Deep reasoning or long-context (> 8k, code audit, multi-file): Kimi k2 preview or moonshot-128k variants
  - Web research tasks: start with glm-4.5-flash for planning; switch to Kimi for longer synthesis if needed
  - Vision: Kimi models that support images; compress/resample images before upload
- Heuristics (auto)
  - If token estimate > 6k or files > 1: prefer Kimi long-context model
  - If user sets “fast/cheap”: force glm-4.5-flash unless vision/long-context
  - If CJK-heavy input: use improved token estimate; cap max_output_tokens accordingly

## Upload & Caching Policy
- Size guardrails
  - Kimi: enforce KIMI_FILES_MAX_SIZE_MB (default 20)
  - GLM: enforce GLM_FILES_MAX_SIZE_MB (default 50)
- When to upload vs link
  - Upload: when content is local or volatile; cache file_id in session scope
  - Link/URL: for static public resources; fetch with browsing tool and only upload small extracts if needed
- Reuse policy
  - Maintain a per-session FileCache {sha256 -> provider: file_id} with TTL; opt-in env to persist across sessions

## Browsing & Agent Patterns
- Gate browsing
  - Start with “plan-only” using cheap model; confirm goal, constraints, and known facts
  - Allow N hops (default 3–5) with per-hop timeout and domain allowlist
  - Extract citations and store brief note per URL; summarize before asking follow-ups
- Multi-file reasoning
  - Chunk → summarize → synthesize. Summaries feed the final model call; upload full files only if summaries lose critical details

## Token/Latency Controls
- Token estimation
  - CJK-aware heuristic (~0.6 tokens/char) else ~4 chars/token; prefer SDK tokenizers when available
- Timeouts and retries
  - Multipart: per-request timeout (env-controlled); JSON calls with backoff and jitter
- Streaming
  - Enable streaming for exploratory Q&A; disable for deterministic audits to simplify parsing

## Configuration Knobs (recommended defaults)
- DEFAULT_MODEL=glm-4.5-flash
- GLM_API_URL=https://api.z.ai/api/paas/v4  (override if regional)
- KIMI_API_URL=https://api.moonshot.ai/v1
- KIMI_FILES_MAX_SIZE_MB=20, GLM_FILES_MAX_SIZE_MB=50
- GLM_FILE_UPLOAD_TIMEOUT_SECS=180, FILE_UPLOAD_TIMEOUT_SECS=180
- EX_WEBSEARCH_DEFAULT_ON=true with domain allowlist; per-hop timeout 8s; max hops 4

## Implementation Plan (Phased)
- Phase v8: Routing + FileCache
  - Add RouterService: applies heuristics; returns (provider, model, params)
  - Implement FileCache (sha256 keyed) with session TTL; optional persistence
  - Tools call provider.upload_file only through RouterService
- Phase v9: Browsing Controller
  - Add BrowseOrchestrator: plan step, limited hops, summarizer, citations
  - Env knobs: EX_WEBSEARCH_MAX_HOPS, EX_WEBSEARCH_ALLOWED_DOMAINS
- Phase v10: Tokenizer + Metrics
  - Integrate provider SDK tokenizer where possible; fall back to heuristics
  - Emit usage/latency metrics per call; write to JSONL for dashboards

## Risks & Mitigations
- Cost creep with browsing: gate hops/timeouts; summarize aggressively
- Provider drift (APIs/models): maintain feature flags and a conformance test set
- File privacy: prevent uploading sensitive files by default; require explicit consent

## Appendix: Artifacts
- Raw thinkdeep metadata: see 2025-09-09_18-32-08_thinkdeep_agentic_strategy_raw.json
- v6/v7 implementation notes: see prior sweep reports



---

## Addendum (2025-09-10): WS Daemon context and practical patterns
- Environment: EXAI-WS (stdio shim → WS daemon) validated; majority of tools operational
- Model selection: prefer explicit models for consensus and long-context tasks; router heuristics remain applicable
- File uploads: keep per-provider size caps (Kimi 20MB, GLM 50MB), cache file_id by sha256 with session TTL

### End-to-end agentic loop (practical recipe)
1) Plan (glm-4.5-flash): clarify task, constraints, prior knowledge; set budgets
2) Fetch (browse): N≤4 hops, per-hop timeout; collect citations
3) Summarize (glm-4.5-flash): extract key facts and quotes
4) Synthesize (kimi-k2-0905-preview or 128k variant): integrate summaries with citations; enforce token caps
5) Verify (consensus with explicit model): short critique pass; flag missing evidence
6) Finalize: produce answer with citations; persist artifacts (JSONL logs)

### Notes for multi-application usage
- Run independent MCP server entries per client/window; ensure unique server IDs
- Keep ENV_FILE shared; avoid duplicating secrets in client configs
- Observe shim/daemon logs on connect; use UTF-8 and unbuffered Python to avoid encoding stalls
