# Phone Access via Tunnel (Free, Simple)

This lets Claude on your phone reach your laptop’s EX MCP.

## Option A: Cloudflare Tunnel
```bash
# Install cloudflared (see cloudflare docs)
cloudflared tunnel --url http://localhost:7800
```
- Copy the https URL it prints.

## Option B: ngrok
```bash
# Install ngrok
ngrok http 7800
```
- Copy the https forwarding URL.

## Connect Claude mobile
- Server URL: https://YOUR-URL/mcp
- Header: Authorization: Bearer <your MCP_AUTH_TOKEN>
- If CORS blocks, keep `CORS_ORIGINS=*` while testing, then restrict later.

## Tips
- Keep the terminal open (tunnel must stay running)
- Rotate token periodically
- For stability, prefer Cloudflare Tunnel (no time limits)

