## Provider/Model
- Provider: Kimi (Moonshot)
- Model: kimi-k2-0905-preview (OpenAI-compatible; base_url=https://api.moonshot.ai/v1)
- EXAI‑WS MCP tool: chat
- Call duration: ~73s | Tokens: ~1.4k
- One‑line summary: YES — Kimi produced an actionable module map and wiring plan without code dumps.

## Module Map (Add / Update / Remove)

### Add
- src/server/conversation_manager.py
  - In‑memory thread/continuation store (Dict[str, Deque[Dict]]), prune by MAX_THREAD_MESSAGES
  - Helpers: async save(thread_id, messages), load(thread_id), get_cont_id() ULID short id
- src/server/ai_manager.py
  - GLM‑4.5‑flash assisted request classifier and routing policy
  - analyse_request(prompt, files) -> TaskType; route_request(...) -> RoutingDecision
  - enhance_prompt(original, routing) -> str
- src/server/tool_wrapper.py
  - Wrap ToolRegistry tools; inject req_id, timing, model hint; normalise to List[TextContent]
  - Records telemetry.count()/histogram() and uses response_handler to build summaries
- src/server/lifecycle.py
  - start()/stop() coroutines; signal handlers; graceful shutdown; provider client cleanup hooks

### Update (expand existing stubs conservatively)
- src/server/dispatcher.py
  - Real handle_call_tool(name, arguments) using wrapped tools, AI manager, fallback orchestrator, circuit
  - Preserve current behaviour and gating; just move logic out of server.py
- src/server/model_resolver.py
  - If ENABLE_AI_MANAGER true, delegate to AIManager; else current static map
- src/server/response_handler.py
  - Add normalise_to_text_content_list(payload) and build_summary(meta) helpers
- src/server/registry_bridge.py
  - Add get_models_for_tool(tool_name) -> List[str] (hide provider registry iter)
  - (Already added) get_feature_flags() -> Dict[str,bool)
- src/server/env.py
  - (Added) get_feature_flags(); ensure typed timeouts: TOOL_TIMEOUT, PROVIDER_TIMEOUT, UPLOAD_TIMEOUT, etc.
- src/server/telemetry.py
  - Add count(tool, status, provider) and histogram(duration_ms) no‑op fallbacks

### Remove / No‑longer‑needed (defer)
- None in this pass. server.py remains as thin wiring shell; bulk logic is extracted.

## File Summaries (what each file must contain)

- conversation_manager.py
  - State: Dict[str, Deque[Dict]]; MAX_THREAD_MESSAGES env cap
  - API: async save(thread_id, messages), load(thread_id) -> List[Dict]
  - Helper: get_cont_id() ULID or uuid4 short id for envelopes
  - No persistence yet; design seam for P2

- ai_manager.py
  - Uses GLM‑4.5‑flash (fast) for classification; disabled by ENABLE_AI_MANAGER=false
  - Enum TaskType: WEB_RESEARCH, FILE_ANALYSIS, CODE_REVIEW, LONG_CONTEXT, FAST_RESPONSE
  - analyse_request(prompt, files) -> TaskType
  - route_request(task_type, context) -> {provider, model, tools, reasoning}
  - enhance_prompt(original, routing) -> str

- tool_wrapper.py
  - Factory: build_wrapped_tools(tools: Dict[str, Tool]) -> Dict[str, ToolWrapper]
  - ToolWrapper.execute(args): adds req_id, timing; try/except to envelope errors
  - Normalises to List[TextContent]; calls telemetry; uses response_handler to summarise

- lifecycle.py
  - start(): optional uvloop, init telemetry, log "EX‑AI‑MCP ready"
  - stop(): close provider clients, flush telemetry, cancel tasks
  - Register SIGINT/SIGTERM handlers

- dispatcher.py (update)
  - __init__(wrapped_tools, ai_manager, fallback_orchestrator, circuit)
  - handle_call_tool(name, arguments) -> List[TextContent]
  - Resolution order: arguments.model → env default → AI manager → "glm-4.5-flash"
  - Fallback paths: file_chat/chat_with_tools to fallback_orchestrator

- model_resolver.py (update)
  - resolve_for_tool(tool_name, model_hint) respects ENABLE_AI_MANAGER and restrictions

- response_handler.py (update)
  - normalise_to_text_content_list(payload)
  - build_summary(meta)

- registry_bridge.py (update)
  - get_models_for_tool(tool_name)
  - get_feature_flags() (already added)

- env.py (update)
  - get_feature_flags(), get_timeouts()

- telemetry.py (update)
  - count(tool, status, provider), histogram(duration_ms) with logger fallback

## server.py Wiring Plan (no code, just steps)

Imports
- from src.server.logging_config import setup_logging
- from src.server.env import env
- from src.server.registry_bridge import get_tools_dict, get_feature_flags
- from src.server.tool_wrapper import build_wrapped_tools
- from src.server.ai_manager import AIManager
- from src.server.dispatcher import Dispatcher
- from src.server.conversation_manager import ConversationManager
- from src.server.lifecycle import start, stop
- from src.server.fallback_orchestrator import FallbackOrchestrator (existing)
- from src.server.circuit import Circuit (existing)

Sequence
1) env.load_dotenv(); cfg = env.get_server_config(); setup_logging(cfg["log_level"], cfg.get("log_file"), json_format=cfg.get("json_logs", False))
2) await start()
3) features = get_feature_flags(); cm = ConversationManager(); ai = AIManager() if features["ai_manager"] else None
4) tools_raw = get_tools_dict(); tools = build_wrapped_tools(tools_raw)
5) fallback = FallbackOrchestrator(); circuit = Circuit(); disp = Dispatcher(tools, ai, fallback, circuit)
6) Create MCP Server; register handlers: list_tools uses tools.values(); call_tool delegates to disp.handle_call_tool(name, arguments)
7) Run stdio_server(); finally: await stop()

## Execution Plan (Batches)

Batch 1 (≤150 lines per file)
- Add: conversation_manager.py, tool_wrapper.py
- Update: registry_bridge.get_feature_flags (done), env.get_timeouts (small), dispatcher signature only
- Safe restart + validate list_tools and simple chat

Batch 2
- Add: lifecycle.py
- Update: dispatcher.handle_call_tool to use wrappers and fallback orchestrator
- Safe restart + validate provider/file paths and fallback routes

Batch 3
- Add: ai_manager.py (behind ENABLE_AI_MANAGER), wire model_resolver to delegate when enabled
- Update: response_handler (normaliser), telemetry (count/histogram)
- Safe restart + validate routing decisions logged; unpredictable validation prompt

Batch 4
- Minimize server.py per wiring plan; keep old code commented for 1 pass (optional), then remove
- Final restart + end‑to‑end smoke

## Validation Seed
"The jade otter hums in binary under lemon rain — decode its hum into a three‑step deployment checklist."

## Risks and Mitigations
- Behaviour drift during extraction → Mitigate by keeping dispatcher/tool_wrapper as the only execution path and by running a smoke test after each batch.
- Provider registry coupling → Hide reads behind registry_bridge.get_models_for_tool; do not import provider internals in server.py.
- Excessive diffs → Respect 150‑line rule; prefer new files over large in‑place edits.
- Logging format changes → Centralise via logging_config and keep stderr+rotating file parity; don’t change default formats.
- Hidden test dependencies → Keep existing function names/signatures; add wrappers instead of rewriting tool classes.




---

## Session Update — Smart Chat integration and provider tools (GLM manager plan)

Provider/Model: GLM (ZhipuAI) | Model: glm-4.5-flash | Tool: EXAI‑WS MCP chat
One‑line: YES — Integrate Smart behavior into chat, keep SmartChat hidden, expose Kimi/GLM native tools via env allowlist, default GLM for simple prompts, route to Kimi for file/long‑context.

### A) Registry gating (env) — expose Kimi/GLM tools, keep SmartChat hidden
- Keep core gating ON and selectively allow provider tools:
  - TOOLS_CORE_ONLY=true
  - TOOLS_ALLOWLIST=chat,kimi_upload_and_extract,kimi_multi_file_chat,kimi_chat_with_tools,glm_upload_file,glm_multi_file_chat,glm_agent_chat,glm_agent_get_result,glm_agent_conversation
- Do NOT include smart_chat in allowlist (hidden and unnecessary when chat integrates smart logic).
- DISABLED_TOOLS should not contain the above provider tools.

Rationale: We retain a controlled core tool surface while enabling provider‑native capabilities for workflows and internal routing. SmartChat remains hidden and not separately invokable.

### B) tools/chat.py — integrate “always‑smart” behavior internally (minimal diffs)
- Add a tiny internal router that:
  - Defaults to GLM‑4.5‑flash for simple prompts
  - If files attached → call kimi_multi_file_chat (primary) with upload‑by‑reference; fallback inject ≤50KB extracted content
  - If explicit tool_choice or web research desired → call kimi_chat_with_tools (Kimi) or normal chat with use_websearch (GLM) per env
  - If prompt/context length suggests long‑context → prefer Kimi model from env (KIMI_DEFAULT_MODEL)
- Preserve the external tool name/descriptor (still “chat”).
- Do not import/register SmartChat tool; logic stays local to chat.

Patch sketch (conceptual, ~40 lines):
```python
# inside tools/chat.py
from tools.registry import ToolRegistry  # to fetch provider tools

class ChatTool(SimpleTool):
    def __init__(self):
        super().__init__()
        try:
            reg = ToolRegistry(); reg.build_tools()
            self._kimi_mf = reg.get_tool("kimi_multi_file_chat")
            self._kimi_tools = reg.get_tool("kimi_chat_with_tools")
            self._glm_mf = reg.get_tool("glm_multi_file_chat")
        except Exception:
            self._kimi_mf = self._kimi_tools = self._glm_mf = None

    def _should_long_context(self, prompt: str, msgs_len: int) -> bool:
        try:
            return len(prompt) > 800 or msgs_len > 5
        except Exception:
            return False

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        prompt = str(arguments.get("prompt", ""))
        files = arguments.get("files") or []
        use_web = bool(arguments.get("use_websearch", True))
        msgs = self._build_messages(prompt, arguments)

        # File‑centric flow → prefer Kimi multi‑file chat
        if files and self._kimi_mf:
            return await self._kimi_mf.execute({"files": files, "prompt": prompt, "model": os.getenv("KIMI_DEFAULT_MODEL","kimi-k2-0905-preview"), "temperature": arguments.get("temperature", 0.3)})

        # Long‑context or explicit tools → Kimi chat with tools when available
        if (self._should_long_context(prompt, len(msgs)) or arguments.get("tool_choice")) and self._kimi_tools:
            return await self._kimi_tools.execute({"messages": msgs, "model": os.getenv("KIMI_DEFAULT_MODEL","kimi-k2-0905-preview"), "tool_choice": arguments.get("tool_choice","auto"), "temperature": arguments.get("temperature", 0.6), "use_websearch": use_web})

        # Default fast path → GLM simple chat via base implementation
        return await super().execute(arguments)
```

Notes:
- Keep ≤150‑line edits; reuse existing SimpleTool behavior for the “default fast path”.
- Errors fall back to Chat’s base execution to avoid UX regressions.

### C) tools/registry.py — keep SmartChat hidden without breaking
- Do not add SmartChat to allowlist; current visibility map already marks smart_chat as advisory/optional and it is only registered when ENABLE_SMART_CHAT and allowlist permit it. With allowlist excluding it, it remains hidden.
- No change required for visibility constants; provider tools are already in TOOL_MAP and will load when allowlisted.

### D) Provider micro‑tuning (optional)
- src/providers/kimi.py
  - Ensure KIMI_DEFAULT_READ_TIMEOUT_SECS (already present) ≥ 120; KIMI_MF_CHAT_TIMEOUT_SECS ~50; CALL_TIMEOUT ≥ 90 via daemon
  - Continue using idempotency + context‑cache headers (already implemented)
- tools/providers/kimi/kimi_upload.py
  - Retain upload‑by‑reference primary path; cap injected extracted content to ≤50KB in fallback (already implemented)

### E) Validation plan
1) list_tools: verify chat visible; verify kimi_* and glm_* tools are present; smart_chat absent
2) Normal chat: short prompt → GLM fast path
3) Multi‑file chat: 2 small files + prompt → kimi_multi_file_chat primary; confirm non‑empty content

### Env changes (authoritative snippet)
```ini
TOOLS_CORE_ONLY=true
TOOLS_ALLOWLIST=chat,kimi_upload_and_extract,kimi_multi_file_chat,kimi_chat_with_tools,glm_upload_file,glm_multi_file_chat,glm_agent_chat,glm_agent_get_result,glm_agent_conversation
# (Intentionally omit smart_chat to keep it hidden.)
```

### EXAI‑MCP call (GLM) — summary
- Provider: GLM (ZhipuAI)
- Model: glm-4.5-flash
- Tool: chat
- Duration: ~48s | Tokens: ~1.8k
- One‑line: YES — Make chat always‑smart internally; expose provider tools via allowlist; keep SmartChat hidden.


---

## Recovery log — Kimi file-feed attempt and registry state

Summary (from terminal and activity logs):
- Daemon restarted cleanly; registry loaded with core+allowlisted tools:
  - Active: chat, kimi_upload_and_extract, kimi_multi_file_chat, kimi_chat_with_tools, glm_upload_file, glm_multi_file_chat, glm_agent_*
- Multiple Kimi file flows executed historically; earlier runs show intermittent `cancelled` on kimi_multi_file_chat at ~2–5s, but also many successful runs.
- Latest restart confirms providers available: GLM models [glm-4.5, glm-4.5-air, glm-4.5-flash], Kimi models [k2 previews, moonshot v1].

Next-step guardrails:
- Keep EXAI_WS_CALL_TIMEOUT ≥ 180s, KIMI_MF_CHAT_TIMEOUT_SECS ≈ 50s (already set). Intermittent provider cancellations are expected; the tool already retries primary before fallback.
- Validation after edits: list_tools, short chat (GLM fast), 2-file Kimi chat. Capture outputs under augment_review_03/runs/.

Copy-paste readiness: YES — chat.py patch + current Kimi tools are sufficient; no additional scaffolding required.


---

## Batch 0.5 — Provider-thread isolation and Kimi de-dup (pre‑Batch 1 hardening)

Findings (from latest mcp_activity.log):
- GLM chat with model=glm-4.5 was cancelled ~1.97s after start (client_abort_suspected). In the same session, earlier Kimi multi‑file/tool calls also cancelled early while Kimi file uploads succeeded (200 OK), causing duplicate file IDs.
- Likely cause: continuation/thread context linked to prior Kimi session (Moonshot) contaminating a GLM chat attempt, plus aggressive early‑abort guard in the orchestrator.

Actionable patch plan (copy‑paste ready; ≤150 lines per file):
1) tools/chat.py — provider‑aware continuation
   - On inbound continuation_id: resolve last provider for that thread. If provider != requested provider, fork a new thread_id and DO NOT carry over provider‑bound artifacts (file refs, tool states). Optionally copy last N user messages as plain text.
   - Add: def _provider_of(model): return 'glm' if model.startswith('glm-') else 'kimi' if model.startswith('kimi-') or 'moonshot-' in model else 'auto'
2) src/server/conversation_manager.py (or create)
   - Key conversations by (provider, thread_id) instead of just thread_id. Provide helpers: get(thread_id, provider), set(...), fork(thread_id, provider)->new_thread_id.
3) server.py — ModelResolver guard
   - Before dispatch: assert provider(model) == selected_provider. If mismatch, hard‑route to correct provider and clear any Kimi‑specific request params.
4) src/providers/kimi.py — checksum de‑dup for uploads
   - Compute sha256(file_bytes); in small in‑memory cache with TTL (e.g., 72h), reuse stored file_id if present. Log reuse vs upload.
5) Orchestrator early‑abort threshold
   - Raise client_abort_suspected threshold for chat + multi‑file/tool flows from ~2s → 8s; add one backoff retry (250–500ms) before cancel.

Minimal skeletons (import‑safe):
- src/server/conversation_manager.py
  ```python
  try:
      from typing import List, Dict, Any
      import uuid
      class ConversationManager:
          def __init__(self): self._store: Dict[str, List[Dict[str, Any]]] = {}
          def _key(self, thread_id: str, provider: str) -> str: return f"{provider}:{thread_id}"
          def load(self, thread_id: str, provider: str): return self._store.get(self._key(thread_id, provider), [])
          def save(self, thread_id: str, provider: str, msgs): self._store[self._key(thread_id, provider)] = msgs
          def fork(self, thread_id: str, provider: str) -> str: nid = uuid.uuid4().hex[:12]; self.save(nid, provider, []); return nid
  except Exception:  # import-safe no-op
      ConversationManager = object  # type: ignore
  ```

- tools/chat.py (excerpt idea)
  ```python
  def _provider_of(model: str) -> str:
      m = (model or '').lower()
      if m.startswith('glm-'): return 'glm'
      if m.startswith('kimi-') or 'moonshot-' in m: return 'kimi'
      return 'auto'
  ```

Kimi checksum de‑dup (src/providers/kimi.py; ≤50 lines idea):
```python
from hashlib import sha256
import time

class _UploadCache:
    def __init__(self, ttl_sec: int = 72*3600):
        self.ttl = ttl_sec; self._m = {}
    def get(self, h):
        v = self._m.get(h); return v['id'] if v and (time.time()-v['ts'] < self.ttl) else None
    def set(self, h, file_id):
        self._m[h] = {'id': file_id, 'ts': time.time()}

_upload_cache = _UploadCache()

def upload_file(self, path: str, purpose: str = 'file-extract'):
    data = open(path, 'rb').read()
    h = sha256(data).hexdigest()
    cached = _upload_cache.get(h)
    if cached:
        self.logger.info(f"Reusing Kimi file_id from cache: {cached}")
        return {'id': cached}
    resp = self._upload_to_kimi_api(data, purpose)  # existing call
    fid = resp['id']
    _upload_cache.set(h, fid)
    return resp
```

Validation steps (record outputs under docs/augment_reports/augment_review_03/runs/):
1) list_tools → confirm chat, glm_*, kimi_* present; SmartChat absent.
2) GLM fast chat (glm-4.5-flash) — unpredictable one‑liner → expect 200 OK.
3) GLM quality chat (glm-4.5) — new thread (no continuation_id) → expect 200 OK.
4) Kimi multi‑file chat — two tiny files; verify no duplicate uploads (cache reuse logged) and no early cancel (<8s threshold).
5) Append raw model outputs + tool summaries to the run log; note any cancels with timestamps.

Delta vs original plan:
- Adds Batch 0.5 hardening before Batch 1 extraction: provider‑thread isolation, checksum de‑dup, and early‑abort tuning to stabilize routes and reduce duplication.
- Keeps Batch 1 server.py reduction scope unchanged but safer to execute next.
