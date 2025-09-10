# EXAI MCP Server Overview (Detailed)

This document explains how the EXAI MCP server in this repository works, how it integrates with providers (Kimi/Moonshot, GLM/ZhipuAI, etc.), and how to interact with it in practice.

## What is MCP here?
- The server implements the Model Context Protocol (MCP) over stdio; the Augment VS Code extension launches it and consumes tools exposed by the server.
- Tools include: thinkdeep, analyze, consensus, chat, orchestrate_auto, challenge, listmodels, version, and project-specific utilities.
- Requests and responses flow through stdio; the extension shows tool outputs and progress logs.

## Provider architecture
- Providers live under `src/providers/` and are registered via `ModelProviderRegistry`.
- Kimi (Moonshot): implemented with an OpenAI-compatible client; supports chat, files API (upload/list/content/delete), and embeddings.
- GLM (ZhipuAI): uses the official SDK when available, with HTTP fallback for uploads; base URL unified to `https://api.z.ai/api/paas/v4`.
- OpenAI-compatible base: shared request/response logic, retries, timeouts, model validation, and vision payload formatting.

## Key recent hardening
- Uploads: per-request timeouts for multipart, size guardrails (env-configurable), clear logging.
- Single-instance lock: PID mutex in `scripts/mcp_server_wrapper.py` to avoid duplicate servers.
- Token awareness: CJK-aware token estimation for better cost/latency planning.

## How tools work
- Tools accept a structured prompt plus optional `relevant_files` and `use_websearch=true` to browse official docs.
- The tool framework token-budgets file embeddings; when attachments are large, tools degrade gracefully or request trimmed excerpts.
- Outputs are summarized into markdown reports under `docs/sweep_reports/...` with timestamps.

## Using file uploads with Kimi
- Upload local files with purpose `file-extract`; then retrieve parsed text via `client.files.content(file_id).text`.
- Delete files with `client.files.delete(file_id=...)` (OpenAI-compatible DELETE /files/{file_id}).
- Use the helper `tools/kimi_files_cleanup.py` to list or delete old files (>N days) with dry-run by default.

## Using embeddings
- Near term: use Kimi embeddings via `client.embeddings.create(model=..., input=[...])`. See `tools/kimi_embeddings.py`.
- Long term: decouple retrieval; compute/store embeddings in your system (vector DB); at query time, send top-k snippets to Kimi/GLM chat. MCP remains for orchestration and chat.

## Cost- and token-aware routing (typical defaults)
- Quick Q&A: `glm-4.5-flash` (fast/economical)
- Long-context/deep synthesis: Kimi long-context models
- Web research: plan on a cheaper model, synthesize on a longer-context model if needed
- Vision: Kimi vision-capable models; compress images prior to upload

## Configuration knobs (env)
- `KIMI_API_URL`, `KIMI_API_KEY`, optional `KIMI_EMBED_MODEL`
- `GLM_API_URL`, `GLM_API_KEY`, upload timeouts
- `KIMI_FILES_MAX_SIZE_MB`, `GLM_FILES_MAX_SIZE_MB`, global `FILE_UPLOAD_TIMEOUT_SECS`
- Web browsing limits (max hops, per-hop timeout, domain allowlist) via tool parameters/config

## Typical workflows
1) Doc-grounded analysis: call `thinkdeep` with `use_websearch=true` and pass authoritative URLs; attach only necessary files.
2) File Q&A: upload via Kimi, retrieve content, and include in messages; or pass file_ids where supported.
3) Research: plan → browse with hop/time limits → cite → synthesize.
4) Embeddings: generate embeddings with Kimi now, or plug in external embeddings later; build a retrieval-augmented chat flow.

## Where results go
- Reports and analyses saved to `docs/sweep_reports/<phase>/...` and `docs/sweep_reports/thinkdeep/...`.
- Personal/system documentation: `docs/personal/`.

## Safety and operations
- Dry-run for any destructive action (cleanup) by default.
- No dependencies installed or env mutated at runtime without explicit approval.
- Logs clearly indicate model routing, file embedding budgets, and failures.

## Next improvements (suggested)
- RouterService to centralize cost-aware model selection.
- BrowseOrchestrator to formalize plan-first, limited-hops browsing with citations.
- ExternalEmbeddingsProvider interface for seamless swap-in of your embedding pipeline.

