# Phase 5 EXAI Plan — Provider parity, external embeddings adapter, routing & ops

Date: 2025-09-09
Scope: Finish GLM parity; introduce external embeddings adapter; tighten routing, guardrails, and ops

## EXAI (thinkdeep, trimmed) consultation summary
- Provider parity: implement GLM file lifecycle tools mirroring Kimi; align timeouts/guardrails
- Embeddings strategy: move to provider-agnostic external embeddings adapter; use Kimi/GLM embeddings only as interim
- Routing: formalize a RouterService with cost/latency/model-capability signals; preflight model availability to avoid split-brain
- Token & context hygiene: excerpt selection + budgets; prefer citations/URLs over raw dumps; progressive disclosure for large contexts
- Ops: add metrics for file counts, cleanup actions, upload sizes, token usage; integrate dry-run safeguards

## Objectives
1) GLM parity to Kimi
   - Complete tools/glm_files_cleanup.py execution once env is set (GLM_API_URL, GLM_API_KEY)
   - Optional: GLM embeddings utility for short-term parity (or skip per adapter plan)
2) External embeddings adapter (provider-agnostic)
   - Define interface: ExternalEmbeddingsProvider with method embed(texts: List[str]) -> List[List[float]]
   - Implement first adapter (e.g., your core system or a cloud vector service)
   - Wire selection via env: EMBEDDINGS_PROVIDER=external|kimi|glm
   - Keep Kimi/GLM utilities as fallback smoke tests
3) RouterService + availability preflight
   - Centralize model selection logic with cost/latency caps and capabilities
   - Add provider availability probes (listmodels + trivial chat) at server start/reload
   - Log chosen routes; expose health status in a /health tool
4) Browse/Docs orchestrator improvements
   - Add minimal browse orchestrator that fetches docs and extracts only relevant sections
   - Cache fetched docs; respect robots/crawl budgets; dedupe by URL hash
5) Observability & guardrails
   - Add metrics: token usage, file counts per provider, cleanup deletions, error rates
   - Enforce configurable size limits on uploads; per-request timeouts; single-instance mutex already present

## Deliverables checklist
- [x] GLM cleanup executed successfully (older-than-days=3); results appended to Phase 4 doc
- [x] ExternalEmbeddingsProvider interface + env routing implemented
- [x] Adapter CLI implemented (tools/embed_router.py) and smoke tested locally
- [ ] RouterService with model availability preflight and decision logging
- [ ] Browse orchestrator with doc slicing and cache
- [ ] Metrics: counters + simple CSV or JSONL logs in ./logs/

## Risks & mitigations
- Missing env for GLM: mitigate by .env.sample + startup checks
- Rate limiting on file operations: implement backoff + pagination
- Token overruns: strict excerpting + per-tool budgets
- Embedding dimensional mismatch: validate dims on ingestion; store metadata with provider and dim

## Runbook (when ready)
- Set env for GLM:
  - set GLM_API_URL=https://api.z.ai/api/paas/v4
  - set GLM_API_KEY=***
- Run GLM cleanup (real):
  - python -X utf8 tools/glm_files_cleanup.py --older-than-days 3 --no-dry-run
- Select embeddings provider (external recommended):
  - set EMBEDDINGS_PROVIDER=external
- Smoke tests:
  - python -X utf8 tools/kimi_embeddings.py --text "hello world"
  - (adapter) python -m your_adapter_cli --text "hello world"



## Implemented in this pass
- src/embeddings/provider.py: provider-agnostic adapter (external, kimi) + selector
- tools/embed_router.py: CLI to test embeddings routing; auto-loads .env
- tools/glm_files_cleanup.py: .env auto-load added; parity cleanup executed (0 deletions)
- tools/kimi_files_cleanup.py: .env auto-load added; real delete executed (0 deletions)
- scripts/mcp_server_wrapper.py: PID-aware stale-lock handling to prevent false "another instance" blocks


---

## Addendum (2025-09-10): EXAI-WS validation and near-term focus
- EXAI-WS daemon/shim validated; majority of tools confirmed working via activity logs and smoke tests
- Consensus: use explicit model (e.g., glm-4.5-flash or kimi-k2-0711-preview) rather than "auto"
- Pending tool capture to complete in Phase 5: orchestrate_auto, kimi_chat_with_tools, kimi_upload_and_extract, secaudit, testgen
- Documentation: toolkit snapshot added at docs/architecture/toolkit/EXAI_Toolkit_Report_2025-09-10.md

### Updated Deliverables timeline (incremental)
- [ ] RouterService with availability preflight (listmodels + trivial chat) and decision logging
- [ ] Browse orchestrator (doc slicing + cache + citations)
- [ ] Metrics (token usage, file counts, deletions, error rates)
- [ ] Conformance tests: consensus (explicit model), orchestrate_auto, kimi_* tools, secaudit/testgen
- [ ] Embeddings provider selector (EMBEDDINGS_PROVIDER) and first external adapter

### Ops checklist for multi-app MCP instances (Windows)
- Separate EXAI-WS server entries per client/window (unique server IDs)
- Ensure each shim uses ENV_FILE and unbuffered UTF-8 (`-u`, PYTHONIOENCODING=utf-8)
- Verify Output→Augment/“Augment MCP” or logs/ws_shim.log on first connect after updates


---

## Tool captures (2025-09-10)
- kimi_chat_with_tools: OK ("ACK")
- kimi_upload_and_extract: OK (EXAI_Toolkit_Report_2025-09-10.md uploaded; file_id=d30finamisdua6ggt6l0)
- orchestrate_auto: invoked; channel returned no body; manual version/models check confirms version=5.8.5, models=18
- secaudit (scripts/run_ws_shim.py): invoked; channel returned no body
- testgen (tools/ws_daemon_smoke.py): invoked; channel returned no body

Follow-up
- Add explicit capture mode for secaudit/testgen/orchestrate_auto to persist results to docs/sweep_reports in the next sweep.
