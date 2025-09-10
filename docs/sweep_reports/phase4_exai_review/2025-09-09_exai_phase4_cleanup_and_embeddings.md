# Phase 4 EXAI Review — Kimi Cleanup (>3 days), Embeddings Strategy (Tier 2)

Date: 2025-09-09
Scope: Kimi file lifecycle, near-term embeddings via Kimi, long-term external embeddings; GLM follow-up noted

## 1) EXAI consultation (Kimi Files API)
- Source: https://platform.moonshot.ai/docs/api/files#request-address-1
- Findings (OpenAI-compatible conventions):
  - List: `GET /files` (SDK: `client.files.list(limit=...)`), returns `data: [...]`
  - Retrieve content: `GET /files/{file_id}/content` (SDK: `client.files.content(file_id).text`)
  - Delete: `DELETE /files/{file_id}` (SDK: `client.files.delete(file_id=...)`), idempotent per id
  - Practical: paginate or request larger `limit` to avoid rate spikes; batch deletes with backoff

Decision: Use `client.files.delete(file_id=...)` and filter locally by created_at to delete items older than threshold.

## 2) Cleanup implementation (>3 days)
- New behavior:
  - tools/kimi_files_cleanup.py: support `--older-than-days N` (dry-run by default)
  - Example: delete items older than 3 days (UTC midnight):
    - Dry-run: `python -X utf8 tools/kimi_files_cleanup.py --older-than-days 3`
    - Real delete: `python -X utf8 tools/kimi_files_cleanup.py --older-than-days 3 --no-dry-run`
- Safety: default dry-run; prints items before deletion; errors counted and reported
- Notes: For very large accounts, consider pagination; current approach requests a large limit (up to 1000)

## 3) EXAI consultation (Embeddings, Tier 2)
- Question: As Tier 2, should we use Kimi embeddings now and later switch to external embeddings? Can MCP remain for chat while retrieval uses our vectors?
- Guidance (doc-grounded + best practice):
  - Short-term: use Kimi embeddings endpoint via OpenAI-compatible SDK (e.g., `client.embeddings.create(model=..., input=[...])`)
  - Long-term: decouple retrieval/embedding from chat. Use your own embedding pipeline + vector store. At query time, retrieve top-k passages and send them to Kimi/GLM as context. Kimi does not require that embeddings used for retrieval come from Kimi.
  - Compliance: avoid uploading sensitive data; store embeddings and documents in your system; only send minimal excerpts to models as needed.

Decision: Implement a thin Kimi embeddings tool now and keep adapter points open for external embeddings later.

## 4) Embeddings implementation (now) and future adapter
- New utility: tools/kimi_embeddings.py
  - Reads `KIMI_EMBED_MODEL` from env
  - Supports `--text` or `--file` (newline-separated) inputs
  - Calls `client.embeddings.create(model=..., input=[...])`
  - Prints JSONL with vector dims (optional vectors)
- Future adapter (planned):
  - Add an `ExternalEmbeddingsProvider` interface and a registry entry
  - Configure via env to route embeddings to external service; keep Kimi route as fallback

## 5) What we did in code (this phase)
- Updated: tools/kimi_files_cleanup.py — added `--older-than-days` and threshold calculation
- Added: tools/kimi_embeddings.py — minimal embeddings generator via Kimi

## 6) Validation plan
- Dry-run cleanup: run `--older-than-days 3` and verify the list aligns with expectations
- Optional real delete: re-run with `--no-dry-run`
- Embeddings smoke test: set `KIMI_EMBED_MODEL`, embed a few lines, verify dims non-empty

## 6.1) Execution results (today)
- Kimi cleanup dry-run (>3 days): Matched 0 files before UTC midnight threshold; no deletions performed
- Kimi cleanup real delete (>3 days): Completed; Deleted=0, Errors=0
- Improvement: Kimi CLI now auto-loads .env, so keys are picked up without manual export
- Listing (limit 200) shows recent activity only; retention policy currently leaves you well below the 1,000-file cap
- Thinkdeep (trimmed) confirmation: Kimi deletion via DELETE /files/{id} is correct; embeddings via embeddings.create acceptable short-term; long-term external embeddings recommended with RAG

## 7) GLM parity (implementation + execution)
- Implementation:
  - Added: tools/glm_files_cleanup.py — list and delete via GLM API (GET /files, DELETE /files/{id}); defaults to dry-run
  - Mirrors Kimi cleanup semantics: --older-than-days N, --list/--limit, --no-dry-run
  - Uses utils.HttpClient with GLM_API_URL + GLM_API_KEY
- Execution result (today):
  - Completed: matched 0 files older than 3 days; Deleted=0, Errors=0
  - Improvement: CLI now auto-loads .env, so keys are picked up without manual export
- Embeddings note:
  - For parity, we can add a GLM embeddings utility; however, long-term plan prioritizes external embeddings adapter shared across providers.

## Appendix: Commands
- List recent files:
  - `python -X utf8 tools/kimi_files_cleanup.py --list --limit 200`
- Delete >3 days (dry-run):
  - `python -X utf8 tools/kimi_files_cleanup.py --older-than-days 3`
- Delete >3 days (real):
  - `python -X utf8 tools/kimi_files_cleanup.py --older-than-days 3 --no-dry-run`
- Embeddings:


  - `set KIMI_EMBED_MODEL=<your-embed-model>`
  - `python -X utf8 tools/kimi_embeddings.py --text "hello world"`
  - `python -X utf8 tools/kimi_embeddings.py --file samples.txt --no-vectors`



## Appendix: Trimmed EXAI thinkdeep consultation (validation)
- Model routing observed: initial attempt glm-4.5-flash -> router resolved to kimi-k2-0905-preview for synthesis
- File embedding cap encountered on earlier run; trimmed re-run succeeded with minimal attachments
- Confirmations:
  - Kimi deletion: DELETE /files/{id} (SDK: client.files.delete) is recommended; batch with backoff
  - Kimi embeddings: embeddings.create is appropriate short-term; decouple retrieval long-term
  - GLM parity: provide analogous /files list + delete utility; keep timeouts/guardrails symmetrical
- Recommendations captured in this report and implemented via tools


---

## 8) EXAI-WS status update (2025-09-10)
- WebSocket daemon (127.0.0.1:8765): healthy; tools count = 21 (validated by tools/ws_daemon_smoke.py)
- Stdio shim: updated to new MCP stdio stream API, unified .env load, UTF‑8 + unbuffered; initializes and lists tools correctly
- Verified working tools via EXAI-WS: version, listmodels, provider_capabilities, activity, chat, thinkdeep, planner, challenge, analyze, codereview, debug, docgen, precommit, refactor, tracer
- Partial: consensus requires an explicit model (e.g., glm‑4.5‑flash or kimi‑k2‑0711‑preview); model="auto" is not available
- Pending capture (registered, re-run recommended): orchestrate_auto, kimi_chat_with_tools, kimi_upload_and_extract, secaudit, testgen

## 9) Pluggable embeddings (design note)
- New selector: EMBEDDINGS_PROVIDER=external|kimi|glm (proposed)
- Near-term: Kimi embeddings utility in place for quick RAG prototypes
- Long-term: ExternalEmbeddingsProvider interface as the single entrypoint; adapters for in-house vectors and cloud vectors
- Retrieval guidance: keep embeddings/doc storage in your system; fetch top‑k; send minimal, cited excerpts to providers

## 10) Action items carried forward
- Implement embeddings provider selector and first external adapter
- Exercise pending EXAI‑WS tools individually and attach outputs to the next sweep report
- Add basic conformance tests for consensus (explicit model), orchestrate_auto, kimi_* tools, and secaudit/testgen

---

## Appendix: EXAI-WS tool captures (2025-09-10)
- kimi_chat_with_tools (model=kimi-k2-0711-preview): output="ACK" (tokens: prompt=28, completion=2, total=30)
- kimi_upload_and_extract: uploaded docs/architecture/toolkit/EXAI_Toolkit_Report_2025-09-10.md → file_id=d30finamisdua6ggt6l0; extracted text available for chat completions
- orchestrate_auto (health check): no return payload in channel; manual verification via version/listmodels → version=5.8.5; models=18; providers=Kimi✅ GLM✅
- secaudit (OWASP scan on scripts/run_ws_shim.py): invocation recorded; no return payload captured in this channel
- testgen (for tools/ws_daemon_smoke.py): invocation recorded; no return payload captured in this channel

Notes:
- Some tools complete without streaming their body back through this channel. Activity logs may still show TOOL_COMPLETED. For deeper captures, re-run individually and persist outputs to docs/sweep_reports.

