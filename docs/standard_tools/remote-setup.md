# EX MCP Server - Remote Mode Setup Guide

This guide explains how to run EX MCP Server as a network-accessible MCP endpoint over HTTP/SSE without launching it as a local subprocess. It covers token setup, CORS, TLS, and common deployment options.

## Overview

- Transport: HTTP with Server-Sent Events (SSE) and optional WebSockets
- App: FastAPI app (remote_server.py)
- Paths:
  - MCP base path: /mcp (configurable)
  - Alternate paths (also mounted): /sse, /v1/sse
  - Health: /healthz
- Auth: Bearer token via MCP_AUTH_TOKEN
- CORS: Allowlist origins with CORS_ORIGINS

## Prerequisites

- Python 3.10+
- Your EX MCP Server checkout
- Optionally Docker/Compose for containerized deployment

## Install remote extras

```bash
pip install .[remote]
# Installs: fastapi, uvicorn[standard], sse-starlette, fastmcp
```

## Start the server (direct uvicorn)

```bash
# Required in production
export MCP_AUTH_TOKEN="your-strong-shared-secret"

# Recommended
export MCP_REMOTE_HOST=0.0.0.0
export MCP_REMOTE_PORT=7800
export MCP_BASE_PATH=/mcp
export CORS_ORIGINS=https://your-ui.example.com

# Start
uvicorn remote_server:app --host ${MCP_REMOTE_HOST:-0.0.0.0} --port ${MCP_REMOTE_PORT:-7800}
```

Endpoints:
- http(s)://<host>:7800/mcp (primary)
- http(s)://<host>:7800/sse and /v1/sse (alternate mounts)
- http(s)://<host>:7800/healthz

## Generating an MCP_AUTH_TOKEN

MCP_AUTH_TOKEN is an arbitrary shared secret used as a Bearer token. You can:

- Generate on Linux/macOS:
```bash
python - <<'PY'
import secrets; print(secrets.token_urlsafe(32))
PY
```
- Generate on Windows PowerShell:
```powershell
[Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```
- Or standard password managers / vaults (recommended for production)

Set the token as an environment variable on the server host:
```bash
export MCP_AUTH_TOKEN=the-generated-token
```

Clients must send the header:
```
Authorization: Bearer the-generated-token
```

## CORS and security

- Always set CORS_ORIGINS to a specific list in production, e.g.:
```bash
export CORS_ORIGINS=https://your-ui.example.com,https://another.example.com
```
- Terminate TLS at a reverse proxy (Caddy/NGINX/Cloudflare Tunnel) and forward to the app.
- Keep MCP_AUTH_TOKEN private; rotate periodically.
- Consider IP allowlists and rate-limiting at the proxy.

## Docker Compose with Caddy (HTTPS)

A ready-to-use setup is included:

- docker-compose.remote.yml
- Caddyfile

Steps:
```bash
export MCP_AUTH_TOKEN=$(python - <<'PY'
import secrets; print(secrets.token_urlsafe(32))
PY)

docker compose -f docker-compose.remote.yml up -d
```

Caddy will terminate TLS on 443 and reverse-proxy /mcp, /sse, /v1/sse to the EX MCP container.

## NGINX example

The repository includes nginx.conf showing how to route the same paths to the EX MCP service.

## Client configuration

Support for MCP-over-URL varies by client. Where supported, configure:
- URL: https://your-domain/mcp (or /sse, /v1/sse)
- Headers: Authorization: Bearer <MCP_AUTH_TOKEN>
- Ensure the client origin is included in CORS_ORIGINS on the server

If your editor/agent expects stdio-only MCP, you can still connect to EX MCP via the usual local subprocess method. Remote mode is an alternative for clients that support URL transports.

## Troubleshooting

- 401 Unauthorized: Ensure Authorization header uses the correct token.
- CORS errors in browser/UIs: Check CORS_ORIGINS and proxy headers.
- SSE stalls behind proxies: Disable proxy buffering for SSE (examples provided in Caddyfile/nginx.conf).
- Alt path not found: Verify MCP_BASE_PATH and that /sse or /v1/sse are mounted.

## Reference

- Module: remote_server.py
- Extras: [remote] in pyproject.toml
- Compose/proxies: docker-compose.remote.yml, Caddyfile, nginx.conf

