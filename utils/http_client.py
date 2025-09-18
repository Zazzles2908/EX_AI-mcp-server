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
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_key_header = api_key_header
        self.api_key_prefix = api_key_prefix
        # Allow environment override for HTTP timeout (in seconds)
        try:
            _env_timeout = float(os.getenv("EX_HTTP_TIMEOUT_SECONDS", str(timeout)))
        except Exception:
            _env_timeout = timeout
        self._timeout = _env_timeout
        self._client = httpx.Client(timeout=self._timeout, follow_redirects=True)

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

