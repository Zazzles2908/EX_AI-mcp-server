from __future__ import annotations

import os
from typing import Any, Dict
from pathlib import Path



import json
from tools.shared.base_tool import BaseTool
from tools.shared.base_models import ToolRequest
from src.providers.glm import GLMModelProvider

from src.providers.registry import ModelProviderRegistry


class GLMUploadFileTool(BaseTool):
    name = "glm_upload_file"
    description = (
        "Upload a file to ZhipuAI GLM Files API (purpose=agent by default) and return its file id."
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
                "file": {"type": "string", "description": "Path to file (abs or relative)"},
                "purpose": {"type": "string", "enum": ["agent"], "default": "agent"},
            },
            "required": ["file"],
        }

    def get_request_model(self):
        return ToolRequest

    def prepare_prompt(self, request: ToolRequest) -> str:
        # No unified prompt; this tool performs provider upload directly
        return ""

    def get_system_prompt(self) -> str:
        return (
            "You handle GLM file upload to support downstream agent or chat tasks.\n"
            "Parameters:\n- file: Path to a single file (abs or relative).\n- purpose: 'agent' (default).\n\n"
            "Behavior:\n- POST {GLM_API_URL}/files with Bearer auth; returns an id.\n- This tool does not retrieve file content (API does not expose it).\n\n"
            "Safety:\n- Respect provider limits (~100MB/file). Treat returned file_id as opaque; do not rely on its format.\n- Avoid uploading sensitive content unnecessarily.\n\n"
            "Output: Raw JSON fields commonly include {file_id, filename, bytes?}; content retrieval is not supported by this tool."
        )


    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.get_input_schema(),
        }

    def run(self, **kwargs) -> Dict[str, Any]:
        file_path = kwargs.get("file")
        purpose = (kwargs.get("purpose") or "agent").strip()
        if not file_path:
            raise ValueError("file is required")

        # Resolve provider and use provider-level upload implementation
        prov = ModelProviderRegistry.get_provider_for_model(os.getenv("GLM_QUALITY_MODEL", "glm-4.5"))
        if not isinstance(prov, GLMModelProvider):
            api_key = os.getenv("GLM_API_KEY", "")
            if not api_key:
                raise RuntimeError("GLM_API_KEY is not configured")
            prov = GLMModelProvider(api_key=api_key)

        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # FileCache: reuse existing file_id if enabled and present
            from pathlib import Path as _P
            from utils.file_cache import FileCache
            cache_enabled = os.getenv("FILECACHE_ENABLED", "true").strip().lower() == "true"
            file_id = None
            if cache_enabled:
                try:
                    pth = _P(str(p))
                    sha = FileCache.sha256_file(pth)
                    fc = FileCache()
                    cached = fc.get(sha, "GLM")
                    if cached:
                        try:
                            from utils.observability import record_cache_hit
                            record_cache_hit("GLM", sha)
                        except Exception:
                            pass
                        file_id = cached
                    else:
                        try:
                            from utils.observability import record_cache_miss
                            record_cache_miss("GLM", sha)
                        except Exception:
                            pass
                except Exception:
                    file_id = None

            if not file_id:
                file_id = prov.upload_file(str(p), purpose=purpose)
                # on new upload, cache it
                try:
                    if cache_enabled:
                        pth = _P(str(p))
                        sha = FileCache.sha256_file(pth)
                        fc = FileCache()
                        fc.set(sha, "GLM", file_id)
                except Exception:
                    pass
                # Observability: record file count +1
                try:
                    from utils.observability import record_file_count
                    record_file_count("GLM", +1)
                except Exception:
                    pass
            return {"file_id": file_id, "filename": p.name}
        except Exception as e:
            try:
                from utils.observability import record_error
                record_error("GLM", os.getenv("GLM_QUALITY_MODEL", "glm-4.5"), "upload_error", str(e))
            except Exception:
                pass
            raise

    async def execute(self, arguments: dict[str, Any]) -> list["TextContent"]:
        import asyncio as _aio
        from mcp.types import TextContent
        result = await _aio.to_thread(self.run, **arguments)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

class GLMMultiFileChatTool(BaseTool):
    name = "glm_multi_file_chat"
    description = (
        "Upload multiple files to GLM (purpose=agent), then call chat/completions with those files summarized as system content."
    )

    def get_system_prompt(self) -> str:
        return (
            "You orchestrate GLM multi-file chat.\n"
            "Purpose: Upload files (purpose 'agent'), include a system preamble enumerating uploaded files, then ask user's prompt.\n\n"
            "Parameters: files, prompt, model, temperature.\n"
            "Notes:\n- GLM upload returns ids; content retrieval is not available here.\n- Include filenames as context to guide the model, but do not expose ids in final answer.\n"
            "Output: Concise answer informed by listed files and user prompt."
        )

    def get_descriptor(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}},
                    "prompt": {"type": "string"},
                    "model": {"type": "string", "default": os.getenv("GLM_QUALITY_MODEL", "glm-4.5")},
                    "temperature": {"type": "number", "default": 0.3},
                },
                "required": ["files", "prompt"],
            },
        }

    def run(self, **kwargs) -> Dict[str, Any]:
        files = kwargs.get("files") or []
        prompt = kwargs.get("prompt") or ""
        model = kwargs.get("model") or os.getenv("GLM_QUALITY_MODEL", "glm-4.5")
        temperature = float(kwargs.get("temperature") or 0.3)
        if not files or not prompt:
            raise ValueError("files and prompt are required")

        # Upload files to GLM (purpose=agent); GLM docs do not expose a direct retrieve content API akin to Kimi's file-extract
        uploaded = []
        for fp in files:
            up = GLMUploadFileTool().run(file=fp, purpose="agent")
            uploaded.append(up)

        # For parity with Kimi chat flow, we will include placeholders listing filenames.
        # If/when GLM exposes content retrieval for uploaded files, we can fetch and include their text like Kimi.
        sys_msg = "\n".join([f"[GLM Uploaded] {u['filename']} (id={u['file_id']})" for u in uploaded])

        # Resolve provider from registry; fallback to direct client if missing
        prov = ModelProviderRegistry.get_provider_for_model(model)
        if not isinstance(prov, GLMModelProvider):
            api_key = os.getenv("GLM_API_KEY", "")
            if not api_key:
                raise RuntimeError("GLM_API_KEY is not configured")
            prov = GLMModelProvider(api_key=api_key)

        # Call provider using normalized API
        mr = prov.generate_content(prompt=prompt, model_name=model, system_prompt=sys_msg, temperature=temperature)
        return {"model": model, "content": mr.content, "uploaded": uploaded}

