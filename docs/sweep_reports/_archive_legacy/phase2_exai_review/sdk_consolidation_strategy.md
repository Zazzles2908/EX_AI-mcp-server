# SDK Consolidation Strategy — OpenAI, GLM (ZhipuAI), and Kimi/Moonshot

Date: 2025-09-09
Owner: EXAI MCP Server

## Executive Summary
We will standardize on:
- Kimi/Moonshot: Use the official OpenAI Python library with base_url and MOONSHOT_API_KEY (Moonshot’s API is explicitly OpenAI‑compatible).
- GLM (ZhipuAI): Use the official ZhipuAI Python SDK (`zhipuai`) for first‑class features and stability.
- OpenAI/Generic OpenAI‑compatible endpoints (including our OpenRouter path): Use the official OpenAI Python library (`openai`).

Rationale
- Minimizes complexity while using vendor‑preferred SDKs (ZhipuAI native) and the widely supported OpenAI SDK for OpenAI‑compatible providers (Kimi, OpenRouter, local OA‑compatible).
- Improves maintainability and reduces bugs from custom HTTP glue.
- Preserves advanced features (streaming, retries, timeouts) via official clients.

## Authoritative Sources (web)
- OpenAI Python library (official): https://github.com/openai/openai-python
- GLM / ZhipuAI SDK (PyPI): https://pypi.org/project/zhipuai/
- Kimi/Moonshot (OpenAI‑compatible):
  - “Our API is fully compatible with the OpenAI API format; you can directly use the official OpenAI SDK (Python/Node). Set base_url=https://api.moonshot.cn/v1 and use MOONSHOT_API_KEY.” (Moonshot docs, Quickstart/Chat API)
  - Docs portal: https://platform.moonshot.ai/ (Chat API, Quickstart, Migration from OpenAI)

## Repository implementation status (validated via EXAI MCP)
- Kimi/Moonshot provider: now uses the OpenAI-compatible base (OpenAI SDK) with Moonshot base_url.
  - Evidence: src/providers/kimi.py subclasses OpenAICompatibleProvider and passes base_url=https://api.moonshot.cn/v1; HttpClient usage removed from request path.
  - Status: DONE (migrated to OpenAI SDK).
- GLM (ZhipuAI) provider: now prefers the official `zhipuai` SDK with HTTP fallback when SDK unavailable.
  - Evidence: src/providers/glm.py initializes ZhipuAI client inside __init__ and uses SDK in generate_content; if import/init fails, falls back to HttpClient.
  - Status: PARTIAL DONE (SDK path primary; HTTP fallback retained for environments without the SDK).
- OpenRouter provider: already aligned with strategy (OpenAI SDK via OpenAI-compatible base).
  - Evidence: src/providers/openrouter.py extends OpenAICompatibleProvider (line 17) and sets base_url to https://openrouter.ai/api/v1 (line 42);
    providers/openai_compatible.py builds an OpenAI client with api_key/base_url and robust timeouts.
- Registry/env: .env is loaded from the repo root early in src/providers/registry.py (lines 14–19), ensuring ENV is available when launched via MCP or CLI.

### ENV checklist (runtime)
- Kimi/Moonshot: MOONSHOT_API_KEY (or KIMI_API_KEY per your env naming), optional KIMI_API_URL override; allowed list via KIMI_ALLOWED_MODELS.
- GLM (ZhipuAI): ZHIPUAI_API_KEY, optional GLM_API_URL override; allowed list via GLM_ALLOWED_MODELS.
- OpenRouter: OPENROUTER_API_KEY, optional OPENROUTER_REFERER and OPENROUTER_TITLE headers.
- DEFAULT_MODEL for final fallback and model routing, if used.


## How we will use each library

### 1) OpenAI Python library (for OpenAI/OpenRouter/Kimi)
- Client creation:
  - OpenAI: `OpenAI(api_key=OPENAI_API_KEY)`
  - Kimi/Moonshot: `OpenAI(api_key=MOONSHOT_API_KEY, base_url="https://api.moonshot.cn/v1")`
  - OpenRouter: `OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")`
- Chat Completions or Responses API per official examples.
- Streaming, retries (default 2 with exponential backoff), and timeouts configurable via client options.

### 2) ZhipuAI Python SDK (GLM native)
- Client: `from zhipuai import ZhipuAI; client = ZhipuAI(api_key=ZHIPUAI_API_KEY)`
- Chat completions: `client.chat.completions.create(model="glm-4.5-flash", messages=[...])`
- Supports streaming, timeouts (via httpx), and extra_body for parameters.
- Optional base_url override: `https://open.bigmodel.cn/api/paas/v4/`

### 3) When to use OpenAI‑compatible vs native
- Kimi/Moonshot: Use OpenAI SDK (recommended by vendor; simpler and officially supported as OA‑compatible).
- GLM (ZhipuAI): Use native `zhipuai` SDK for best support and evolving features. If needed, we can retain an OpenAI‑compatible path via OpenRouter or a compatibility layer, but native remains primary.

## Concrete usage examples

OpenAI (Kimi via base_url):
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["MOONSHOT_API_KEY"],
    base_url="https://api.moonshot.cn/v1",
)
resp = client.chat.completions.create(
    model="kimi-k2-0905-preview",
    messages=[{"role": "user", "content": "Hello from Kimi via OpenAI SDK"}],
)
print(resp.choices[0].message.content)
```

ZhipuAI (GLM native):
```python
from zhipuai import ZhipuAI
import os

client = ZhipuAI(api_key=os.environ["ZHIPUAI_API_KEY"])  # Optionally base_url=...
resp = client.chat.completions.create(
    model="glm-4.5-flash",
    messages=[{"role": "user", "content": "Hello from GLM via native SDK"}],
)
print(resp.choices[0].message.content)
```

OpenRouter (OpenAI‑compatible):
```python
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)
resp = client.chat.completions.create(
    model="anthropic/claude-3.5-sonnet",
    messages=[{"role": "user", "content": "Hello via OpenRouter"}],
)
print(resp.choices[0].message.content)
```

## Integration into our codebase (src/providers)
- Kimi provider: uses OpenAI client via OpenAICompatibleProvider with Moonshot base_url + MOONSHOT_API_KEY. Capability logic and allow-list preserved. Custom HTTP glue removed.
- GLM provider: uses `zhipuai` client for chat completions by default; falls back to HTTP if SDK is not installed. ModelResponse normalized for both paths.
- OpenRouter provider: continue using OpenAI SDK with OpenRouter base_url + API key.
- Keep the existing registry for model routing, allow-lists, and DEFAULT_MODEL fallback. No external behavior change for tools.

## Error handling & Observability
- OpenAI SDK: use built-in retries (tune via `max_retries`), set `timeout`, capture `_request_id` when present.
- ZhipuAI SDK: configure `timeout` (httpx), `max_retries` as available in SDK, and catch `APIStatusError`, `APITimeoutError` etc. per docs.
- Uniform logging in providers to include provider name, model, latency, and request id where available.

## Migration plan (phased)
1) Introduce clients via small factory helpers (so tests can inject fakes):
   - get_openai_client(kind) → returns OpenAI client for OpenAI/Kimi/OpenRouter with correct base_url/API key.
   - get_zhipu_client() → returns ZhipuAI client.
2) Refactor src/providers/kimi.py to OpenAI SDK usage (remove custom HTTP layer). — DONE
3) Refactor src/providers/glm.py to ZhipuAI SDK usage (if not already done). — DONE (with HTTP fallback retained)
4) Keep interfaces stable (ModelProvider, ModelResponse) and routing unchanged.
5) Update docs/tools examples to reflect new, cleaner SDK usage.

## Risks and mitigations
- Different response shapes: We adapt once in provider layer to our unified ModelResponse struct.
- Env/config drift: Centralize env-to-client mapping (API keys, base_url) in one place; validate on startup.
- Streaming differences: Normalize provider streaming into a common iterator yielding content deltas.

## Next actions
- Implement client factories and refactor Kimi + GLM providers to the SDKs as above.
- Update docs and tools examples.
- Run EXAI MCP sweep + review to validate behavior.



## MCP validation result (latest)
- Attempted to run an EXAI MCP review directly against this repo. The tool session reported no models available ({}), so chat-based review could not proceed.
- Likely causes in client/runtime:
  - The MCP client did not start the server from this project root or with the repo's virtualenv, so .env was not loaded (python-dotenv missing in that interpreter), resulting in no providers.
  - Registration used a direct call to `python server.py` from a non-venv Python or wrong working directory, bypassing .venv and .env loading.
- Remediation (update client MCP registration to use the wrapper):
  - Command: `python -u scripts/mcp_server_wrapper.py`
  - This wrapper resolves the repo root, ensures `.venv` Python is used, sets PYTHONPATH/cwd, and then imports `server.run()`.
  - If your client supports an ENV file path, set ENV_FILE to this repo's `.env` as an extra guarantee.
- After updating registration, validate within the MCP UI: list models → test Kimi (e.g., `kimi-k2-0905-preview`) and GLM (`glm-4.5-flash`).

Notes
- Server-side code now recognizes vendor env aliases (MOONSHOT_API_KEY/ZHIPUAI_API_KEY) and uses refactored providers (Kimi via OpenAI SDK path; GLM via `zhipuai` when available). If `zhipuai` is not installed in the environment the MCP client launches, GLM will log a warning and fall back to HTTP.
