from __future__ import annotations

import json
import os
import asyncio
import logging

from typing import Any, Dict, List
from pathlib import Path

from mcp.types import TextContent

from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from src.providers.kimi import KimiModelProvider
from src.providers.registry import ModelProviderRegistry


class KimiUploadAndExtractTool(BaseTool):
    def get_name(self) -> str:
        return "kimi_upload_and_extract"

    def get_description(self) -> str:
        return (
            "Upload one or more files to Moonshot (Kimi) using the Files API, extract parsed text, "
            "and return messages you can inject into chat/completions (system-role)."
        )

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of file paths (absolute or relative to project root)",
                },
                "purpose": {
                    "type": "string",
                    "enum": ["file-extract", "assistants"],
                    "default": "file-extract",
                },
            },
            "required": ["files"],
        }

    def get_system_prompt(self) -> str:
        return (
            "You are a precise file-ingestion assistant for Moonshot (Kimi).\n"
            "Purpose: Upload one or more local files to Kimi Files API and return parsed text as system messages.\n\n"
            "Parameters:\n- files: list of file paths (abs/relative).\n- purpose: 'file-extract' (default) or 'assistants'.\n\n"
            "Constraints & Safety:\n- Respect provider limits (e.g., ~100MB/file). If KIMI_FILES_MAX_SIZE_MB is set, prefer skipping larger files locally; provider still enforces hard limits.\n- Do not include secrets or private data unnecessarily.\n\n"
            "Output:\n- Return a JSON array of messages preserving original file order, each: {role: 'system', content: '<extracted text>', _file_id: '<id>'}.\n- Keep content as-is; do not summarize or transform."
        )

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def format_response(self, response: str, request: ToolRequest, model_info: dict | None = None) -> str:
        return response

    def _resolve_path(self, p: str) -> str:
        """Resolve file path against project root when relative.
        Order: absolute -> EX_PROJECT_ROOT -> PROJECT_ROOT -> CWD.
        """
        try:
            from pathlib import Path as _P
            _p = _P(str(p))
            if _p.is_absolute() and _p.exists():
                return str(_p)
            roots = [os.getenv("EX_PROJECT_ROOT"), os.getenv("PROJECT_ROOT"), os.getcwd()]
            for r in [x for x in roots if x]:
                cand = _P(r) / str(p)
                if cand.exists():
                    return str(cand)
            # Fall back to original string; provider may still handle
            return str(_p if _p.is_absolute() else _P(os.getcwd()) / str(p))
        except Exception:
            return str(p)

    def _run(self, **kwargs) -> List[Dict[str, Any]]:
        files = kwargs.get("files") or []
        purpose = (kwargs.get("purpose") or "file-extract").strip()
        if not files:
            raise ValueError("No files provided")

        # Resolve provider
        prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
        if not isinstance(prov, KimiModelProvider):
            api_key = os.getenv("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY is not configured")
            prov = KimiModelProvider(api_key=api_key)

        messages: List[Dict[str, Any]] = []
        from utils.tool_events import ToolCallEvent, ToolEventSink
        sink = ToolEventSink()
        for idx, fp in enumerate(files, start=1):
            resolved = self._resolve_path(fp)
            evt = ToolCallEvent(provider=prov.get_provider_type().value, tool_name="file_upload_extract", args={"path": str(resolved), "purpose": purpose})
            try:
                # Optional local size skip to avoid provider 4xx on large files
                try:
                    max_mb_env = os.getenv("KIMI_FILES_MAX_SIZE_MB", "").strip()
                    if max_mb_env:
                        max_bytes = float(max_mb_env) * 1024 * 1024
                        sz = Path(str(resolved)).stat().st_size
                        if sz > max_bytes:
                            try:
                                logging.getLogger("mcp_activity").warning(
                                    f"[KIMI_UPLOAD] skip {resolved} size={sz}B exceeds {max_mb_env}MB"
                                )
                            except Exception:
                                pass
                            evt.end(ok=False, error=f"skipped: exceeds {max_mb_env}MB")
                            try:
                                sink.record(evt)
                            except Exception:
                                pass
                            continue
                except Exception:
                    pass
                # FileCache: reuse existing file_id if enabled and present
                from pathlib import Path as _P
                from utils.file_cache import FileCache
                cache_enabled = os.getenv("FILECACHE_ENABLED", "true").strip().lower() == "true"
                file_id = None
                prov_name = prov.get_provider_type().value
                if cache_enabled:
                    try:
                        pth = _P(str(resolved))
                        sha = FileCache.sha256_file(pth)
                        fc = FileCache()
                        cached = fc.get(sha, prov_name)
                        if cached:
                            # cache hit
                            try:
                                from utils.observability import record_cache_hit
                                record_cache_hit(prov_name, sha)
                            except Exception:
                                pass
                            file_id = cached
                        else:
                            try:
                                from utils.observability import record_cache_miss
                                record_cache_miss(prov_name, sha)
                            except Exception:
                                pass
                    except Exception:
                        file_id = None

                if not file_id:
                    file_id = prov.upload_file(resolved, purpose=purpose)
                    # on new upload, cache it
                    try:
                        if cache_enabled:
                            pth = _P(str(resolved))
                            sha = FileCache.sha256_file(pth)
                            fc = FileCache()
                            fc.set(sha, prov.get_provider_type().value, file_id)
                    except Exception:
                        pass
                    # Observability: record file count +1 for fresh upload
                    try:
                        from utils.observability import record_file_count  # lazy import
                        record_file_count(prov.get_provider_type().value, +1)
                    except Exception:
                        pass

                # Retrieve parsed content with retry/backoff (provider may throttle on multiple files)
                def _fetch():
                    attempts = int(os.getenv("KIMI_FILES_FETCH_RETRIES", "3"))
                    backoff = float(os.getenv("KIMI_FILES_FETCH_BACKOFF", "0.8"))
                    delay = float(os.getenv("KIMI_FILES_FETCH_INITIAL_DELAY", "0.5"))
                    last_err = None
                    for _ in range(attempts):
                        try:
                            return prov.client.files.content(file_id=file_id).text
                        except Exception as e:
                            last_err = e
                            # backoff before retry
                            try:
                                import time as _t
                                _t.sleep(delay)
                            except Exception:
                                pass
                            delay *= (1.0 + backoff)
                    if last_err:
                        raise last_err
                    raise RuntimeError("Failed to fetch file content (unknown error)")
                # Apply a hard cap to total fetch duration to avoid indefinite block
                import concurrent.futures as _fut
                fetch_timeout = float(os.getenv("KIMI_FILES_FETCH_TIMEOUT_SECS", "25"))
                try:
                    with _fut.ThreadPoolExecutor(max_workers=1) as _pool:
                        _future = _pool.submit(_fetch)
                        content = _future.result(timeout=fetch_timeout)
                except _fut.TimeoutError:
                    raise TimeoutError(f"Kimi files.content() timed out after {int(fetch_timeout)}s for file_id={file_id}")
                messages.append({"role": "system", "content": content, "_file_id": file_id})
                evt.end(ok=True)
            except Exception as e:
                evt.end(ok=False, error=str(e))
                # Observability: record provider error
                try:
                    from utils.observability import record_error
                    record_error(prov.get_provider_type().value, getattr(prov, 'FRIENDLY_NAME', 'Kimi'), 'upload_error', str(e))
                except Exception:
                    pass
                raise
            finally:
                try:
                    sink.record(evt)
                except Exception:
                    pass
        return messages
    def _upload_files_only(self, *, files: List[str], purpose: str = "file-extract") -> List[str]:
        """Upload files to Moonshot and return their file_ids without extracting content.
        Primary purpose is to enable reference-based chat without content injection.
        """
        if not files:
            return []
        # Resolve provider
        prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
        if not isinstance(prov, KimiModelProvider):
            api_key = os.getenv("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY is not configured")
            prov = KimiModelProvider(api_key=api_key)
        file_ids: List[str] = []
        for fp in files:
            try:
                resolved = self._resolve_path(fp)
                fid = prov.upload_file(resolved, purpose=purpose)
                if fid:
                    file_ids.append(str(fid))
            except Exception as e:
                # Continue best-effort; log via mcp_activity
                try:
                    logging.getLogger("mcp_activity").warning(f"[KIMI_UPLOAD_ONLY] failed for {resolved}: {e}")
                except Exception:
                    pass
        return file_ids


    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        # Offload blocking provider/file I/O to a background thread to avoid blocking event loop
        import asyncio as _aio
        from tools.shared.error_envelope import make_error_envelope
        try:
            msgs = await _aio.to_thread(self._run, **arguments)
            return [TextContent(type="text", text=json.dumps(msgs, ensure_ascii=False))]
        except Exception as e:
            env = make_error_envelope("KIMI", self.get_name(), e)
            return [TextContent(type="text", text=json.dumps(env, ensure_ascii=False))]



class KimiMultiFileChatTool(BaseTool):
    name = "kimi_multi_file_chat"
    description = (
        "Upload multiple files to Kimi, extract content, prepend as system messages, then call chat/completions."
    )

    # BaseTool required interface
    def get_name(self) -> str:
        return self.name

    def get_description(self) -> str:
        return self.description

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "files": {"type": "array", "items": {"type": "string"}},
                "prompt": {"type": "string"},
                "model": {"type": "string", "default": os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")},
                "temperature": {"type": "number", "default": 0.3},
            },
            "required": ["files", "prompt"],
        }

    def get_request_model(self):
        return ToolRequest

    def prepare_prompt(self, request: ToolRequest) -> str:
        # This tool performs provider calls directly; no unified prompt needed
        return ""

    def get_system_prompt(self) -> str:
        return (
            "You orchestrate Kimi multi-file chat.\n"
            "Purpose: Upload N files, extract their text, prepend each as a system message, then ask the user prompt.\n\n"
            "Parameters:\n"
            "- files: List of paths (absolute or relative under project root).\n"
            "- model: Kimi model id (defaults via KIMI_DEFAULT_MODEL).\n"
            "- temperature: Sampling temperature.\n\n"
            "Notes:\n"
            "- Extraction uses Kimi Files API (purpose 'file-extract'); content is added verbatim as system-role context messages.\n"
            "- Do not echo large file content verbatim in the final answer; provide concise, synthesized results.\n"
            "- Provider limits apply (e.g., ~100MB/file).\n"
            "Output: A concise answer to the user prompt informed by the provided files."
        )

    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Multi-file chat flow (robust):
        1) Primary: upload files only (no large content injection) and prompt the model
           to use the attached files by reference.
        2) Fallback: if response content is empty or cancelled, inject extracted content
           but cap total injected bytes to 50KB to avoid provider cancellation.
        3) Timeout: default 80s (configurable via KIMI_MF_CHAT_TIMEOUT_SECS).
        Returns a structured dict with model, content, and diagnostics.
        """
        import concurrent.futures as _fut
        import os
        from pathlib import Path as _P

        files = kwargs.get("files") or []
        prompt = kwargs.get("prompt") or ""
        model = kwargs.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
        temperature = float(kwargs.get("temperature") or 0.3)

        if not files or not prompt:
            raise ValueError("files and prompt are required")

        # Provider
        prov = ModelProviderRegistry.get_provider_for_model(os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
        if not isinstance(prov, KimiModelProvider):
            api_key = os.getenv("KIMI_API_KEY", "")
            if not api_key:
                raise RuntimeError("KIMI_API_KEY is not configured")
            prov = KimiModelProvider(api_key=api_key)
        # Context cache/idempotency hints
        try:
            import uuid
            session_id = os.getenv("EX_SESSION_ID") or f"mcp-{os.getpid()}"
            call_key = str(uuid.uuid4())
        except Exception:
            session_id, call_key = None, None


        # Primary: upload files only (no content injection)
        upload_tool = KimiUploadAndExtractTool()
        try:
            file_ids = upload_tool._upload_files_only(files=files, purpose="file-extract")
        except Exception:
            # If upload helper not available or fails, continue with empty attachments list
            file_ids = []

        # Lightweight system hint listing filenames (not contents)
        try:
            _names = [(_P(str(f)).name) for f in files]
        except Exception:
            _names = []
        file_note = ("Attached files: " + ", ".join(_names)) if _names else ""
        system_hint = {
            "role": "system",
            "content": ("Use the attached files by reference to answer accurately. " + file_note).strip(),
        }
        messages = [system_hint, {"role": "user", "content": prompt}]

        def _call_primary():
            return prov.chat_completions_create(
                model=model,
                messages=messages,
                temperature=temperature,
                _session_id=session_id,
                _call_key=call_key,
                _tool_name=self.get_name(),
            )

        timeout_s = float(os.getenv("KIMI_MF_CHAT_TIMEOUT_SECS", "80"))
        _retry_backoff = float(os.getenv("KIMI_MF_RETRY_BACKOFF_SECS", "0.5"))
        try:
            with _fut.ThreadPoolExecutor(max_workers=1) as _pool:
                _future = _pool.submit(_call_primary)
                resp = _future.result(timeout=timeout_s)
        except _fut.TimeoutError:
            raise TimeoutError(f"Kimi multi-file chat timed out after {int(timeout_s)}s")
        except Exception as _e1:
            # One retry with short backoff before switching to content-injection fallback
            try:
                import time as _time
                _time.sleep(_retry_backoff)
                with _fut.ThreadPoolExecutor(max_workers=1) as _pool:
                    _future2 = _pool.submit(_call_primary)
                    resp = _future2.result(timeout=timeout_s)
            except Exception:
                # Re-raise original to let structured envelope path handle it
                raise _e1

        content = (resp or {}).get("content", "")
        if content:
            return {"model": model, "content": content, "file_ids": file_ids or []}

        # Fallback: inject extracted content, but cap to 50KB
        sys_msgs = upload_tool._run(files=files)
        MAX_BYTES = int(os.getenv("KIMI_MF_INJECT_MAX_BYTES", "51200"))  # 50KB default
        used = 0
        trimmed_msgs: list[dict[str, str]] = []
        for m in sys_msgs:
            try:
                text = str(m.get("content", ""))
            except Exception:
                text = ""
            if not text:
                continue
            b = text.encode("utf-8", errors="ignore")
            if used >= MAX_BYTES:
                break
            remain = MAX_BYTES - used
            if len(b) > remain:
                text = b[:remain].decode("utf-8", errors="ignore")
            used += len(text.encode("utf-8", errors="ignore"))
            trimmed_msgs.append({"role": "system", "content": text})

        messages_fb = [*trimmed_msgs, {"role": "user", "content": prompt}]

        def _call_fallback():
            return prov.chat_completions_create(
                model=model,
                messages=messages_fb,
                temperature=temperature,
                _session_id=session_id,
                _call_key=call_key,
                _tool_name=self.get_name(),
            )

        try:
            with _fut.ThreadPoolExecutor(max_workers=1) as _pool:
                _future = _pool.submit(_call_fallback)
                resp2 = _future.result(timeout=timeout_s)
        except _fut.TimeoutError:
            raise TimeoutError(f"Kimi multi-file chat (fallback) timed out after {int(timeout_s)}s")

        content2 = (resp2 or {}).get("content", "")
        return {
            "model": model,
            "content": content2,
            "used_fallback": True,
            "file_ids": file_ids or [],
            "injected_bytes": used,
        }

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        import asyncio as _aio
        try:
            # Hard-cap total execution time to ensure progress and enable fallback
            try:
                timeout_s = float(os.getenv("KIMI_MF_CHAT_TIMEOUT_SECS", "80"))
            except Exception:
                timeout_s = 80.0
            result = await _aio.wait_for(_aio.to_thread(self.run, **arguments), timeout=timeout_s)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except _aio.TimeoutError:
            err = {
                "status": "execution_error",
                "error_class": "timeouterror",
                "provider": "KIMI",
                "tool": self.get_name(),
                "detail": f"kimi_multi_file_chat exceeded {int(timeout_s)}s (execute cap)",
            }
            return [TextContent(type="text", text=json.dumps(err, ensure_ascii=False))]
        except Exception as e:
            # Emit a structured error envelope so the dispatcher can fallback
            err = {
                "status": "execution_error",
                "error_class": type(e).__name__.lower(),
                "provider": "KIMI",
                "tool": self.get_name(),
                "detail": str(e),
            }
            return [TextContent(type="text", text=json.dumps(err, ensure_ascii=False))]
