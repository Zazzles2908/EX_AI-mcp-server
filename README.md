# EX MCP Server

EX MCP Server is a Model Context Protocol (MCP) server that connects modern LLM providers and tools to MCP‑compatible clients (e.g., Claude Desktop/CLI). It provides a unified set of analysis, debugging, refactoring, documentation, testing, and project automation tools accessible over the MCP stdio protocol.

## Key Capabilities
- Unified MCP server exposing rich development tools:
  - analyze, codereview, debug, refactor, tracer, testgen, precommit, listmodels, version
- Provider integrations:
  - KIMI (Moonshot), GLM (Zhipu), OpenRouter, and custom OpenAI‑compatible endpoints
- MCP‑first architecture:
  - Subprocess stdio transport with direct config examples for Claude Desktop/CLI
- Docker and local dev support:
  - Docker image build/publish, local virtualenv (.venv), and cross‑platform scripts

## Installation

### Prerequisites
- Python 3.9+
- Git
- For local dev: virtualenv support
- Optional: Docker and Docker Compose

### Clone
```
git clone https://github.com/BeehiveInnovations/ex-mcp-server.git
cd ex-mcp-server
```

### Setup (local)
```
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
pip install -r requirements-dev.txt

cp .env.example .env
# Set at least one provider key (KIMI_API_KEY, GLM_API_KEY, OPENROUTER_API_KEY, or CUSTOM_API_URL/CUSTOM_API_KEY)
```

### Run (local)
```
python -m server   # or: python server.py
```

### Configure a client (Claude Desktop/CLI)
Minimal example (stdio):
```
{
  "mcpServers": {
    "ex": {
      "type": "stdio",
      "trust": true,
      "command": "python",
      "args": ["-u", "scripts/mcp_server_wrapper.py"],
      "cwd": "/absolute/path/to/ex-mcp-server",
      "env": {
        "MCP_SERVER_NAME": "ex",
        "MCP_SERVER_ID": "ex-server",
        "PYTHONPATH": "/absolute/path/to/ex-mcp-server",
        "ENV_FILE": "/absolute/path/to/ex-mcp-server/.env"
      }
    }
  }
}
```
See the examples/ directory for more configs (macOS, WSL, desktop CLI variants).

## Docker
Build and run locally:
```
docker build -t ex-mcp-server:latest .
docker run --rm -it ex-mcp-server:latest
```
A reverse proxy example is provided (nginx.conf) and a remote compose file (docker-compose.remote.yml) that exposes the server as ex-mcp.

## Usage Overview
- Use the version tool to verify install:
```
# In Claude Desktop config, call the version tool
```
- Common tools:
  - analyze: smart file analysis
  - codereview: professional code review
  - debug: debugging assistant
  - refactor: code refactoring
  - tracer: static analysis / call chain aid
  - testgen: test generation
  - precommit: quick pre-commit validation
  - listmodels: show available models/providers

### Provider‑native Web Browsing Schemas
- Kimi (Moonshot): inject an OpenAI function tool named "web_search" with a string parameter "query".
- GLM (Zhipu): enable tools = [{"type":"web_search","web_search":{}}] only when allowed by env.
- Set these via env for production readiness:
  - KIMI_ENABLE_INTERNET_TOOL=true and KIMI_INTERNET_TOOL_SPEC to a valid JSON tool schema
  - GLM_ENABLE_WEB_BROWSING=true when appropriate (and other GLM browsing flags as documented)

## Hidden Model Router (Auto Model Selection)
The server can auto-select a concrete model at the MCP boundary so users don’t need to specify one.

- Enable: HIDDEN_MODEL_ROUTER_ENABLED=true
- Sentinels: ROUTER_SENTINEL_MODELS=glm-4.5-flash,auto
- Default: DEFAULT_MODEL=glm-4.5-flash (a sentinel)

Behavior:
- If a tool requires a model and incoming model is a sentinel (or "auto"), the server resolves a concrete model.
- Structured logs emitted by the server (logger name: "server"):
  - EVENT boundary_model_resolution_attempt input_model=... tool=... sentinel_match=... hidden_router=...
  - EVENT boundary_model_resolved input_model=... resolved_model=... tool=...

Notes:
- The Consensus tool intentionally does not resolve models at the MCP boundary (requires_model = False). You will see the "attempt" log at the boundary, and per-step model selection happens inside the tool.

Tip: Use listmodels to see configured providers/models.

## Agentic Audit with Real Models (EX‑AI)
Use a consensus-based, multi-model audit to find issues and get direct fixes.

1) Set provider keys in .env:
- KIMI_API_KEY=...
- GLM_API_KEY=...

2) Run the audit script:
```
python scripts/exai_agentic_audit.py --models glm-4.5-air kimi-k2-0905-preview
```
Or rely on env defaults (GLM_AUDIT_MODEL, KIMI_AUDIT_MODEL) and just:
```
python scripts/exai_agentic_audit.py
```
The script returns JSON:
```
{
  "issues": [ { "title": str, "evidence": str, "direct_fix": str }... ],
  "summary": str
}
```

3) Interpreting results:
- Each issue has “direct_fix” with exactly what to change and where.
- Re-run after fixes to validate improvements.

## Tests: End-to-end (no real keys required)
We include an “ultimate” test file designed for EX‑AI‑style validation:
- tests/test_e2e_exai_ultimate.py
- Each assert prints a Direct Fix if it fails.
- Run: `python -m pytest -q tests/test_e2e_exai_ultimate.py`

### CI/Test Hygiene (EX fork)
This fork disables some upstream providers by design. If you run the full test suite, import errors may occur for those optional providers.
See docs/ci-test-notes.md for ways to skip/guard those tests in CI.

## Configuration
- Environment file: .env (see .env.example for available variables)
- Key variables:
  - DEFAULT_MODEL, LOCALE, MAX_MCP_OUTPUT_TOKENS
  - Provider keys: KIMI_API_KEY, GLM_API_KEY, OPENROUTER_API_KEY
  - Custom API: CUSTOM_API_URL, CUSTOM_API_KEY
- Logging: logs/ directory (Docker and local scripts manage ownership/paths)

## Attribution
This project is based on the original work at:
- https://github.com/BeehiveInnovations/zen-mcp-server
We have forked/copied and adapted it to create EX MCP Server. Attribution to the original authors is preserved.

## Our EX‑specific Changes (Zen → EX)
- Rebranding:
  - Service name: zen-mcp → ex-mcp
  - Non-root user: zenuser → exuser (Dockerfile, file ownership)
  - Virtual environment: .zen_venv → .venv
  - Branding strings: “Zen MCP Server” → “EX MCP Server”
- Examples/configs:
  - Server IDs: "zen" → "ex"
  - Commands: zen-mcp-server → ex-mcp-server
  - Paths updated to ex-mcp-server
- CI/workflows & templates:
  - GitHub discussions/links point to ex-mcp-server
  - GHCR image names: ghcr.io/<org>/ex-mcp-server:...
- Architecture intent:
  - MCP-first stdio transport, reverse proxy alignment, and consistent service naming

## Contributing
Please see CONTRIBUTING.md for development workflow, coding standards, and testing.

## License
See the LICENSE file in this repository.

## Additional Resources
- MCP Spec: https://modelcontextprotocol.io/
- Claude Desktop docs for MCP: https://docs.anthropic.com/claude/docs/model-context-protocol
- Original source (upstream): https://github.com/BeehiveInnovations/zen-mcp-server
- Current project: https://github.com/BeehiveInnovations/ex-mcp-server
