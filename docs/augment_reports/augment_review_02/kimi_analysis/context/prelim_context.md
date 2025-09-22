# Preliminary Context for EXAI-WS Validation (Stage A/B)

Nonce: 7f3bbf3b-7134-495b-9a9f-24b9a3b5a6c1

## Intent
- Enforce timeout precedence: KIMI_MF_CHAT_TIMEOUT_SECS ≤ FALLBACK_ATTEMPT_TIMEOUT_SECS ≤ EXAI_WS_CALL_TIMEOUT
- Avoid per-connection blocking by reconnecting after long/failed kimi_multi_file_chat
- Ensure UI surfacing: always return at least one text block

## Changes (excerpts)

1) WS daemon ceiling tightened (src/daemon/ws_server.py)

```python
# WS-level hard ceiling for a single tool invocation; keep small to avoid client-perceived hangs
CALL_TIMEOUT = int(os.getenv("EXAI_WS_CALL_TIMEOUT", "90"))  # default 90s; can be raised via env if needed
```

2) UI surfacing guard (src/daemon/ws_server.py)

```python
if not outputs_norm:
    outputs_norm = [{"type": "text", "text": ""}]
result_payload = {"op": "call_tool_res", "request_id": req_id, "outputs": outputs_norm}
```

3) Reconnect after Kimi failure to avoid session blocking (scripts/kimi_analysis/run_backend_kimi_analysis.py)

```python
failed = (res.get("error") is not None) or (
    isinstance(res.get("outputs"), dict) and res.get("outputs", {}).get("status") == "cancelled"
)
if failed:
    try:
        await ws.close()
    except Exception:
        pass
    _log_status("reconnect_after_kimi_failure", {"uri": connected_uri})
    ws = await _ws_connect(connected_uri)
    await ws.send(json.dumps({"op": "hello", "session_id": f"kimi-backend-{TS}-re", "token": TOKEN}))
    _ = json.loads(await ws.recv())
    await ws.send(json.dumps({"op": "list_tools"}))
    _ = json.loads(await ws.recv())
```

## Question for the model
Given these excerpts and intent:
- Will the 90s EXAI_WS_CALL_TIMEOUT ceiling combined with the reconnection policy eliminate perceived "no output/hangs" for chat/analyze/thinkdeep during typical operation?
- Identify remaining risks/edge cases (e.g., provider-side long polls, partial progress not surfaced, multiple in-flight tasks per session) and propose guardrails.
- Conclude with: `VERDICT: LIKELY FIXED / PARTIAL / NOT FIXED` and 1–2 lines of rationale.

