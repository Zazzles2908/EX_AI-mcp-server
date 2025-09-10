# Remote Deployment (HTTP/SSE)
> Note: Claude mobile works with remote MCP servers, but you currently add servers via the web interface first; the mobile app then uses those servers. This is a UX flow, not a server limitation.


This guide explains how to run Zen MCP Server as a remote MCP service accessible over the network (for Claude Desktop/CLI or mobile).

## Overview

Zen MCP runs locally over stdio by default. For remote access, we expose the MCP protocol via HTTP using SSE/WebSocket using FastAPI and an adapter.

- Protocol path: configurable via MCP_BASE_PATH (default: /mcp)
- Health check: /healthz
- CORS: configured via CORS_ORIGINS (default: *)
- Auth: Bearer token via MCP_AUTH_TOKEN

## Quickstart (local)

```
pip install .[remote]
export MCP_REMOTE_HOST=0.0.0.0
export MCP_REMOTE_PORT=7800
## HTTPS and Endpoint Patterns

For mobile access use HTTPS on port 443 via a reverse proxy. Supported endpoint patterns:
- https://your-domain.com/sse
- https://your-domain.com/mcp
- https://your-domain.com/v1/sse

Set CORS_ORIGINS to your domain in production (avoid '*').

export MCP_AUTH_TOKEN=your_shared_secret
python -m uvicorn remote_server:app --host ${MCP_REMOTE_HOST} --port ${MCP_REMOTE_PORT}
```
## Reverse Proxy (Caddy)

Use docker-compose.remote.yml to run the app and a Caddy proxy on port 443. Example Caddyfile:

```
# Caddyfile
example.com {
  reverse_proxy /mcp* /sse* /v1/sse* zen-mcp:7800 {
    header_up Authorization {>Authorization}
    header_up X-Forwarded-Proto {scheme}
    header_up X-Forwarded-For {remote}
  }
}
```

## Reverse Proxy (Nginx)

```
server {
  listen 443 ssl http2;
  server_name example.com;
  location ~ ^/(mcp|sse|v1/sse) {
    proxy_pass http://zen-mcp:7800;
    proxy_set_header Authorization $http_authorization;
    proxy_buffering off; # SSE
  }
}
```


## Docker

```
# Build
docker build -f docker/Dockerfile.remote -t zen-mcp-remote .

# Run
docker run -e MCP_AUTH_TOKEN=your_shared_secret -e KIMI_API_KEY=... -e GLM_API_KEY=... \
  -p 7800:7800 zen-mcp-remote
```

## Claude connection examples

Claude Desktop/CLI currently expect stdio transports. For remote connections, use clients that support MCP over URL (SSE/WebSocket). Where supported, configure:

- URL: http(s)://your-host:7800/mcp
- Headers: Authorization: Bearer your_shared_secret
- CORS: Ensure your client origin is allowed (CORS_ORIGINS)

For mobile access via a proxy app or reverse proxy:
- Set CORS_ORIGINS to your mobile app origin or *
- Use HTTPS via your proxy (e.g., Cloudflare Tunnel, Caddy, Nginx)

## Configuration

Environment variables:

```
# Remote server
MCP_REMOTE_HOST=0.0.0.0
MCP_REMOTE_PORT=7800
MCP_BASE_PATH=/mcp
MCP_AUTH_TOKEN=your_shared_secret
CORS_ORIGINS=*

# Providers (Kimi/GLM)
KIMI_API_KEY=...
GLM_API_KEY=...
```

## Observability

- Logs: structured logs to stderr; check logs/mcp_server.log for application logs
- Health: GET /healthz returns { status: "ok", version }

## Cloud deployment tips

- Railway/Render/Heroku: set MCP_REMOTE_PORT to the platform’s port env (e.g., PORT), and run the uvicorn command in the Procfile/
- Use a reverse proxy to terminate TLS and forward to the container’s 7800
- Always set MCP_AUTH_TOKEN and restrict CORS_ORIGINS

