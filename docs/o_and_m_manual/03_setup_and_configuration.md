# Setup & Configuration

## Prerequisites
- Python 3.9+
- Git
- At least one provider key: KIMI_API_KEY or GLM_API_KEY (both recommended)

## .env quick reference
```
# Core
DEFAULT_MODEL=auto                 # enable agentic routing
LOCALE=en-US
MAX_MCP_OUTPUT_TOKENS=2048

# Providers
KIMI_API_KEY=...                   # Kimi/Moonshot
GLM_API_KEY=...                    # GLM (Zhipu)
# Optional OpenAI-compatible
CUSTOM_API_URL=http://localhost:11434
CUSTOM_API_KEY=none

# Router / Behavior
HIDDEN_MODEL_ROUTER_ENABLED=true
ROUTER_SENTINEL_MODELS=glm-4.5-flash,auto
WORKFLOWS_PREFER_KIMI=true         # bias long-context toward Kimi/Moonshot
ENABLE_METADATA_SELECTION=true     # let dispatch hints affect routing

# Tool Surfacing
LEAN_MODE=false
# When LEAN_MODE=true, restrict to this allowlist (comma-separated)
LEAN_TOOLS=status,chat,analyze,codereview,debug,planner,refactor,testgen,thinkdeep,tracer,precommit,secaudit,stream_demo
DISABLED_TOOLS=
```

## Minimal vs. full
- Minimal: one provider key, run `python -m server`, call status/version/listmodels
- Full: both provider keys, DEFAULT_MODEL=auto, tune LEAN_MODE/LEAN_TOOLS as needed

## Install (Windows/macOS/Linux)
```
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
# Add provider keys in .env
```

## Start & verify
```
python -m server
```
- Client: call status, version, listmodels
- Or run smoke:
```
python tools/ws_daemon_smoke.py
```
Expected:
- stream_demo fallback+streaming = success
- thinkdeep web-cue = GLM/Kimi per routing rules
- chat_longcontext = executes; final route depends on size/hints

## Windows notes
- Activate venv: `.venv\Scripts\activate`
- Logs: `Get-Content -Path logs\mcp_activity.log -Tail 200 -Wait`

