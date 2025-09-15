from __future__ import annotations

import json
import os
import asyncio
from typing import Any, Dict, List
from pathlib import Path

from mcp.types import TextContent

from .shared.base_tool import BaseTool
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

    def get_annotations(self) -> dict | None:
        # Provider hint for routers/clients
        return {"provider": "kimi"}

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
            evt = ToolCallEvent(provider=prov.get_provider_type().value, tool_name="file_upload_extract", args={"path": str(fp), "purpose": purpose})
            try:
                # FileCache: reuse existing file_id if enabled and present
                from pathlib import Path as _P
                from utils.file_cache import FileCache
                cache_enabled = os.getenv("FILECACHE_ENABLED", "true").strip().lower() == "true"
                file_id = None
                prov_name = prov.get_provider_type().value
                if cache_enabled:
                    try:
                        pth = _P(str(fp))
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
                    file_id = prov.upload_file(fp, purpose=purpose)
                    # on new upload, cache it
                    try:
                        if cache_enabled:
                            pth = _P(str(fp))
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
                content = _fetch()
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

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        # Offload blocking provider/file I/O to a background thread to avoid blocking event loop
        import asyncio as _aio
        msgs = await _aio.to_thread(self._run, **arguments)
        return [TextContent(type="text", text=json.dumps(msgs, ensure_ascii=False))]
    def get_annotations(self) -> dict | None:
        return {"provider": "kimi"}




class KimiMultiFileChatTool(BaseTool):
    def get_name(self) -> str:
        return "kimi_multi_file_chat"

    def get_description(self) -> str:
        return (
            "Upload multiple files to Kimi, extract content, prepend as system messages, then call chat/completions."
        )

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

    def get_request_model(self):
        return ToolRequest

    def requires_model(self) -> bool:
        return False

    async def prepare_prompt(self, request: ToolRequest) -> str:
        return ""

    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}},
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "default": os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")},
                    "temperature": {"type": "number", "default": 0.3},
                },
                "required": ["files", "prompt"],
            },
        }

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        files = arguments.get("files") or []
        prompt = arguments.get("prompt") or ""
        requested_model = arguments.get("model") or os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
        temperature = float(arguments.get("temperature") or 0.3)

        if not files or not prompt:
            return [TextContent(type="text", text=json.dumps({"error": "files and prompt are required"}))]

        # Enforce provider/model affinity: Kimi tool must use Kimi models
        kimi_models = {
            "kimi-k2-0711","kimi-k2-0711-preview","kimi-k2-0905","kimi-k2-0905-preview",
            "kimi-k2-turbo","kimi-k2-turbo-preview","kimi-latest","kimi-thinking-preview",
            "moonshot-v1-8k","moonshot-v1-32k","moonshot-v1-128k",
            "moonshot-v1-8k-vision-preview","moonshot-v1-32k-vision-preview","moonshot-v1-128k-vision-preview",
        }
        m_lower = str(requested_model).strip().lower()
        if m_lower == "auto" or not any(k in m_lower for k in ["kimi","moonshot-v1"]):
            # Force to default Kimi model if auto or GLM/openrouter was provided
            requested_model = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")

        try:
            # Upload & extract
            upload_tool = KimiUploadAndExtractTool()
            sys_msgs_result = await upload_tool.execute({"files": files})
            sys_msgs = json.loads(sys_msgs_result[0].text)

            # Prepare messages
            messages = [*sys_msgs, {"role": "user", "content": prompt}]

            prov = ModelProviderRegistry.get_provider_for_model(requested_model)
            # Pre-call guard: ensure provider is Kimi
            if not isinstance(prov, KimiModelProvider):
                return [TextContent(type="text", text=json.dumps({
                    "error": "Model/provider mismatch: Kimi tool requires a Kimi model.",
                    "requested_model": requested_model
                }, ensure_ascii=False))]

            # Use OpenAI-compatible client to create completion
            resp = prov.client.chat.completions.create(model=requested_model, messages=messages, temperature=temperature)
            content = resp.choices[0].message.content
            result = {"model": requested_model, "content": content}
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except Exception as e:
            return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
