# Local Quickstart (Personal)

## Install
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Optional: pip install -r requirements-dev.txt
```

## Run stdio (desktop Claude)
```bash
python -m server   # or: ex-mcp-server (after `pip install -e .`)
```

## Run remote (for tunnels)
```bash
pip install .[remote]
# Generate token
python - <<'PY'
import secrets; print(secrets.token_urlsafe(32))
PY
export MCP_AUTH_TOKEN=<paste>
export MCP_BASE_PATH=/mcp
export CORS_ORIGINS=*
uvicorn remote_server:app --host 0.0.0.0 --port 7800
```

Now your local server is ready at http://localhost:7800.

