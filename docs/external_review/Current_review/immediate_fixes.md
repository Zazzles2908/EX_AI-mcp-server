# EX-AI MCP Server: Immediate Fixes Implementation Guide

> Status: APPLIED — All four critical fixes are implemented in code on branch `chore/registry-switch-and-docfix` and ready for validation.

Summary of applied fixes
- Fix #1 (Kimi multi-file chat): Implemented attachment-first flow with fallback injection capped at 50KB and 80s timeout
  - tools/providers/kimi/kimi_upload.py: `_upload_files_only(...)` present; `KimiMultiFileChatTool.run(...)` uses file_ids and a small system hint; fallback injects truncated content
  - Env: `KIMI_MF_CHAT_TIMEOUT_SECS=80` (default), `KIMI_MF_INJECT_MAX_BYTES=51200`
- Fix #2 (Fallback orchestrator): Updated `_is_error_envelope(...)` to only flag explicit error statuses and treat empty/ambiguous as non-errors
  - src/server/fallback_orchestrator.py
- Fix #3 (Response validation): Added `_validate_response_content(...)` and integrated before normalization
  - server.py around ~1607 and call site around ~1757
- Fix #4 (Enhanced logging): Added RESPONSE_DEBUG logs before/after normalization to trace content flow
  - Log markers: `RESPONSE_DEBUG`, `RESPONSE_VALIDATION`, `[FALLBACK]`

EXAI‑WS validation (no terminal)
- Tool: `kimi_multi_file_chat`
- Args:
  - files: ["README.md"]
  - prompt: "Summarize this file in 4 concise bullets; include one ≤5‑line code excerpt; add the phrase 'orchid‑zeppelin 47'"
- Expect:
  - Non‑empty provider content; JSON envelope `status=success`
  - If primary path empties, single retry with `used_fallback=true` and `injected_bytes ≤ 51200`
  - Logs show `RESPONSE_DEBUG` raw/normalized and no spurious `[FALLBACK]` lines

Verification checklist (5)
1) Kimi call returns non‑empty content for the test above
2) No `[FALLBACK] envelope indicates error` when content is present
3) `RESPONSE_DEBUG` shows raw_result_len ≥ 1 and normalized_result_len ≥ 1
4) If fallback used: `used_fallback=true`, `injected_bytes ≤ 51200`
5) Success envelope never has empty `content`; otherwise a validation warning is logged

Notes
- Changes are local only; no pushes/merges were performed
- No dependency changes required


## Critical Fix #1: Kimi Multi-File Chat Response Issue

### Problem
The `KimiMultiFileChatTool` is injecting large extracted file content as system messages, causing Moonshot API to cancel requests rapidly (~5s) without returning content.

### Solution
**File**: `tools/providers/kimi/kimi_upload.py`

Replace the current message construction pattern:

```python
# CURRENT PROBLEMATIC CODE (around line 280):
messages = [*sys_msgs, {"role": "user", "content": prompt}]
```

**With this fixed implementation**:

```python
def run(self, **kwargs) -> Dict[str, Any]:
    files = kwargs.get("files") or []
    prompt = kwargs.get("prompt") or ""
    model = kwargs.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
    temperature = float(kwargs.get("temperature") or 0.3)

    if not files or not prompt:
        raise ValueError("files and prompt are required")

    # FIXED: Use file attachment pattern instead of content injection
    try:
        # Upload files and get file objects (not extracted content)
        upload_tool = KimiUploadAndExtractTool()
        file_objects = upload_tool._upload_files_only(files)  # New method needed

        # Create file-aware message using Moonshot's file attachment pattern
        messages = [{
            "role": "user",
            "content": f"Based on the uploaded files, please {prompt}",
            "attachments": [{"file_id": f["id"], "tools": [{"type": "file_search"}]} for f in file_objects]
        }]

    except Exception as upload_error:
        # Fallback to content-based approach with size limits
        sys_msgs = upload_tool._run(files=files)

        # CRITICAL: Limit system message content to prevent cancellation
        truncated_msgs = []
        total_chars = 0
        max_chars = 50000  # Conservative limit

        for msg in sys_msgs:
            content = msg.get("content", "")
            if total_chars + len(content) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 1000:  # Only include if meaningful content fits
                    truncated_content = content[:remaining] + "\n\n[Content truncated due to size limits]"
                    truncated_msgs.append({"role": "system", "content": truncated_content})
                break
            truncated_msgs.append(msg)
            total_chars += len(content)

        messages = [*truncated_msgs, {"role": "user", "content": prompt}]

    # Rest of implementation remains the same...
    prov = ModelProviderRegistry.get_provider_for_model(model)
    if not isinstance(prov, KimiModelProvider):
        api_key = os.getenv("KIMI_API_KEY", "")
        if not api_key:
            raise RuntimeError("KIMI_API_KEY is not configured")
        prov = KimiModelProvider(api_key=api_key)

    # Execute with proper error handling
    import concurrent.futures as _fut
    def _call():
        return prov.chat_completions_create(model=model, messages=messages, temperature=temperature)

    timeout_s = float(os.getenv("KIMI_MF_CHAT_TIMEOUT_SECS", "80"))
    try:
        with _fut.ThreadPoolExecutor(max_workers=1) as _pool:
            _future = _pool.submit(_call)
            resp = _future.result(timeout=timeout_s)
    except _fut.TimeoutError:
        raise RuntimeError(f"Kimi chat completion timed out after {timeout_s}s")
    except Exception as e:
        raise RuntimeError(f"Kimi chat completion failed: {str(e)}")

    # FIXED: Return structured response with actual content
    try:
        content = ""
        if hasattr(resp, 'choices') and resp.choices:
            choice = resp.choices[0]
            if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                content = choice.message.content or ""

        return {
            "status": "success",
            "content": content,
            "provider": "KIMI",
            "model": model,
            "metadata": {
                "files_processed": len(files),
                "message_approach": "file_attachment" if 'file_objects' in locals() else "content_injection"
            }
        }
    except Exception as e:
        raise RuntimeError(f"Failed to extract response content: {str(e)}")
```

### Additional Method Needed
Add this method to `KimiUploadAndExtractTool`:

```python
def _upload_files_only(self, files: List[str]) -> List[Dict[str, Any]]:
    """Upload files and return file objects without extracting content"""
    prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
    if not isinstance(prov, KimiModelProvider):
        api_key = os.getenv("KIMI_API_KEY", "")
        if not api_key:
            raise RuntimeError("KIMI_API_KEY is not configured")
        prov = KimiModelProvider(api_key=api_key)

    file_objects = []
    for file_path in files:
        try:
            with open(file_path, 'rb') as f:
                file_obj = prov.client.files.create(file=f, purpose="file-extract")
                file_objects.append({"id": file_obj.id, "filename": Path(file_path).name})
        except Exception as e:
            # Log error but continue with other files
            print(f"Failed to upload {file_path}: {e}")
            continue

    return file_objects
```

---

## Critical Fix #2: Fallback Orchestrator False Positives

### Problem
The fallback orchestrator incorrectly identifies successful responses as errors, triggering unnecessary fallbacks.

### Solution
**File**: `src/server/fallback_orchestrator.py`

Replace the `_is_error_envelope` function:

```python
def _is_error_envelope(res: List[TextContent]) -> bool:
    """FIXED: More accurate error detection to reduce false positives"""
    if not res:
        return False  # FIXED: Empty response is not necessarily an error

    try:
        txt = getattr(res[0], "text", None)
        if not isinstance(txt, str) or not txt.strip():
            return False  # FIXED: Empty text is not an error

        try:
            obj = json.loads(txt)
        except Exception:
            # FIXED: Non-JSON responses are not errors (could be plain text success)
            # Only check for obvious error keywords in plain text
            low = txt.lower()
            error_indicators = [
                "execution_error", "cancelled", "timeout",
                "failed to", "error:", "exception:", "traceback"
            ]
            return any(indicator in low for indicator in error_indicators)

        if isinstance(obj, dict):
            # Log envelope for debugging
            try:
                mlog = logging.getLogger("mcp_activity")
                mlog.info(f"[FALLBACK] envelope check: status={obj.get('status')} has_content={bool(obj.get('content'))}")
            except Exception:
                pass

            status = str(obj.get("status", "")).lower()

            # FIXED: Only treat explicit error statuses as failures
            if status in {"execution_error", "cancelled", "failed", "timeout", "error"}:
                return True

            # FIXED: Check for success indicators
            if status in {"success", "ok", "completed"}:
                return False

            # FIXED: If status is unclear, check for actual content
            content = obj.get("content", "")
            if isinstance(content, str) and content.strip():
                return False  # Has content, likely successful

            # FIXED: Check for error field more carefully
            error_field = obj.get("error")
            if error_field and str(error_field).strip():
                return True

    except Exception:
        return False  # FIXED: Don't assume error on parsing failures

    return False  # FIXED: Default to not-error
```

---

## Critical Fix #3: Response Content Validation

### Problem
Responses lose content during serialization/normalization in the server pipeline.

### Solution
**File**: `server.py`

Add this validation function after line 1600:

```python
def _validate_response_content(result: List[TextContent], tool_name: str, req_id: str) -> List[TextContent]:
    """Validate that responses contain actual content, not just metadata"""
    if not result:
        logger.warning(f"[RESPONSE_VALIDATION] Empty result for tool={tool_name} req_id={req_id}")
        return result

    try:
        primary = result[0] if result else None
        if not isinstance(primary, TextContent):
            logger.warning(f"[RESPONSE_VALIDATION] Invalid response type for tool={tool_name} req_id={req_id}")
            return result

        text = primary.text or ""
        if not text.strip():
            logger.warning(f"[RESPONSE_VALIDATION] Empty response text for tool={tool_name} req_id={req_id}")
            return result

        # Try to parse as JSON to check structure
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                content = data.get("content", "")
                status = data.get("status", "")

                # Log content presence for debugging
                logger.info(f"[RESPONSE_VALIDATION] tool={tool_name} req_id={req_id} status={status} has_content={bool(content)} content_length={len(str(content))}")

                # Warn if status is success but no content
                if status == "success" and not str(content).strip():
                    logger.warning(f"[RESPONSE_VALIDATION] Success status but empty content for tool={tool_name} req_id={req_id}")

        except json.JSONDecodeError:
            # Plain text response is fine
            logger.info(f"[RESPONSE_VALIDATION] Plain text response for tool={tool_name} req_id={req_id} length={len(text)}")

    except Exception as e:
        logger.error(f"[RESPONSE_VALIDATION] Validation failed for tool={tool_name} req_id={req_id}: {e}")

    return result
```

Then modify the tool execution section (around line 1650) to use this validation:

```python
# After: result = await _execute_with_monitor(lambda: tool.execute(arguments))
# Add this line:
result = _validate_response_content(result, name, req_id)
```

---

## Critical Fix #4: Enhanced Logging for Debugging

### Problem
Insufficient logging to track where response content is lost.

### Solution
**File**: `server.py`

Add detailed logging around the response processing (around line 1650):

```python
# After tool execution, before normalization
logger.info(f"[RESPONSE_DEBUG] tool={name} req_id={req_id} raw_result_type={type(result)} raw_result_length={len(result) if isinstance(result, list) else 'N/A'}")

if isinstance(result, list) and result:
    for i, item in enumerate(result[:3]):  # Log first 3 items
        if isinstance(item, TextContent):
            text_preview = (item.text or "")[:200] + "..." if len(item.text or "") > 200 else (item.text or "")
            logger.info(f"[RESPONSE_DEBUG] tool={name} req_id={req_id} item_{i}_preview={text_preview}")

# Normalize result shape to list[TextContent]
from mcp.types import TextContent as _TextContent
if isinstance(result, _TextContent):
    result = [result]
elif not isinstance(result, list):
    logger.warning(f"[RESPONSE_DEBUG] tool={name} req_id={req_id} converting_non_list_result type={type(result)}")
    try:
        result = [_TextContent(type="text", text=str(result))]
    except Exception as e:
        logger.error(f"[RESPONSE_DEBUG] tool={name} req_id={req_id} conversion_failed: {e}")
        result = []

# Log after normalization
logger.info(f"[RESPONSE_DEBUG] tool={name} req_id={req_id} normalized_result_length={len(result)}")
```

---

## Implementation Steps

### Step 1: Apply Kimi Fix (Highest Priority)
1. Backup current `tools/providers/kimi/kimi_upload.py`
2. Apply the message construction fix
3. Add the `_upload_files_only` method
4. Test with a simple file upload scenario

### Step 2: Apply Fallback Fix
1. Backup current `src/server/fallback_orchestrator.py`
2. Replace the `_is_error_envelope` function
3. Test fallback behavior

### Step 3: Add Response Validation
1. Add the validation function to `server.py`
2. Integrate it into the response pipeline
3. Monitor logs for content validation issues

### Step 4: Enhanced Logging
1. Add detailed response debugging logs
2. Monitor MCP calls to see where content is lost
3. Use logs to identify any remaining issues

## Testing Commands

After applying fixes, test with:

```bash
# Test Kimi multi-file chat
echo '{"tool": "kimi_multi_file_chat", "arguments": {"files": ["README.md"], "prompt": "Summarize this file"}}' | your_mcp_client

# Monitor logs
tail -f logs/mcp_server.log | grep "RESPONSE_DEBUG\|FALLBACK"
```

## Expected Results

After applying these fixes:
1. ✅ Kimi multi-file chat returns actual response content
2. ✅ Fallback orchestrator only triggers on real errors
3. ✅ Response validation catches content loss issues
4. ✅ Enhanced logging shows exactly where problems occur

These fixes address the core MCP output issue while maintaining system stability.
