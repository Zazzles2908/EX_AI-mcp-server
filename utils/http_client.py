"""
Lightweight HTTP client wrapper used by provider implementations.

Purpose:
- Centralize httpx POST/GET JSON calls
- Apply base URL and API key headers consistently
- Keep dependency surface minimal (no proxies config)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

import httpx


class HttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        api_key_header: str = "Authorization",
        api_key_prefix: str = "Bearer ",
        timeout: float | httpx.Timeout | None = None,
        timeout_prefix: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.api_key_prefix = api_key_prefix

        to = timeout
        if to is None:
            # Build Timeout from environment with optional prefix, e.g., GLM_HTTP_TIMEOUT_CONNECT_SECS
            def _env_to_float(name: str, default: float) -> float:
                try:
                    return float(os.getenv(name, str(default)))
                except Exception:
                    return default
            prefix = (timeout_prefix or "").strip().upper()
            def key(suffix: str) -> str:
                return f"{prefix}_HTTP_TIMEOUT_{suffix}_SECS" if prefix else f"HTTP_TIMEOUT_{suffix}_SECS"
            connect = _env_to_float(key("CONNECT"), 8.0)
            read = _env_to_float(key("READ"), 30.0)
            write = _env_to_float(key("WRITE"), 60.0)
            pool = _env_to_float(key("POOL"), 60.0)
            to = httpx.Timeout(connect=connect, read=read, write=write, pool=pool)

        self._client = httpx.Client(timeout=to, follow_redirects=True)

    @property
    def client(self) -> httpx.Client:
        return self._client

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h[self.api_key_header] = f"{self.api_key_prefix}{self.api_key}" if self.api_key_prefix else self.api_key
        if extra:
            h.update(extra)
        return h

    def _url(self, path: str) -> str:
        if not path:
            return self.base_url
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def post_json(self, path: str, payload: Any, *, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = self._url(path)
        resp = self._client.post(url, headers=self._headers(headers), content=json.dumps(payload))
        resp.raise_for_status()
        # Some APIs may return empty body with 204; normalize to {}
        return resp.json() if resp.content else {}

    def get_json(self, path: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self._url(path)
        resp = self._client.get(url, headers=self._headers(headers), params=params)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

    def delete_json(self, path: str, *, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        url = self._url(path)
        resp = self._client.delete(url, headers=self._headers(headers))
        resp.raise_for_status()
        return resp.json() if resp.content else {}


    def post_multipart(
        self,
        path: str,
        files: dict,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        *,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """POST a multipart/form-data request.

        Content-Type header is omitted so httpx can set the multipart boundary automatically.
        Per-call timeout may be provided to accommodate large uploads.
        """
        url = self._url(path)
        # Build headers without Content-Type to let httpx set boundary
        base_headers = self._headers(headers)
        base_headers.pop("Content-Type", None)
        resp = self._client.post(url, headers=base_headers, files=files, data=data or {}, timeout=timeout)
        resp.raise_for_status()
        return resp.json() if resp.content else {}

