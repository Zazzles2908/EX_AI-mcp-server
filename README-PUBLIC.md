# EX MCP Server

An MCP (Model Context Protocol) server that lets popular coding agents use multiple AI models through one consistent toolset. This fork prioritizes Moonshot/Kimi and ZhipuAI GLM, and optionally supports custom OpenAI-compatible endpoints (e.g., Ollama, vLLM) and OpenRouter.

- First-class: Moonshot/Kimi and GLM
- Optional: Custom OpenAI-compatible endpoints and OpenRouter
- Exposes a rich set of developer-focused tools (code review, debug, refactor, plan, docgen, etc.)
- Runs over stdio as a subprocess of MCP clients (e.g., Claude Code/Claude Desktop)

## Quickstart

Prerequisites: Python 3.10+ (3.12 recommended), Git

1) Clone
```
git clone https://github.com/Zazzles2908/ex-mcp-server.git
cd ex-mcp-server
```

2) Configure environment
```
cp .env.example .env
# Edit .env and set at least one of:
# KIMI_API_KEY=...
# GLM_API_KEY=...
# OPENROUTER_API_KEY=...
# CUSTOM_API_URL=http://localhost:11434/v1  # Ollama example
```

3) Install and run
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
# Optional (dev): pip install -r requirements-dev.txt

# Start the server directly
python -m server  # or: ex-mcp-server (after editable install `pip install -e .`)
```

4) Connect from your MCP client
- Claude Desktop or Claude Code CLI: add a server entry that starts `ex-mcp-server` (see examples below)
- Other MCP clients: configure to launch this repository's entrypoint over stdio

## MCP Client Examples (Claude)

Claude Desktop config snippet (claude_desktop_config.json):
```json
{
  "mcpServers": {
    "ex": {
      "command": "ex-mcp-server",
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin"
      }
    }
  }
}
```

Claude Code CLI project-scoped config (.mcp.json):
```json
{
  "mcpServers": {
    "ex": {
      "command": "ex-mcp-server",
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin"
      }
    }
  }
}
```

Tip: If you prefer zero local setup, you can also launch using uvx from git:
```json
{
  "mcpServers": {
    "ex": {
      "command": "sh",
      "args": ["-c", "exec $(which uvx || echo uvx) --from git+https://github.com/Zazzles2908/ex-mcp-server.git ex-mcp-server"],
      "env": { "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:~/.local/bin" }
    }
  }
}
```

## Configuration

Set environment variables via `.env` or your shell:

Required (any one):
- `KIMI_API_KEY` (Moonshot/Kimi)
- `GLM_API_KEY` (ZhipuAI GLM)
- `OPENROUTER_API_KEY` (OpenRouter)
- `CUSTOM_API_URL` (OpenAI-compatible; e.g., Ollama, vLLM)

Useful options:
- `DISABLED_PROVIDERS` (comma-separated): e.g., `GOOGLE,OPENAI,XAI,DIAL`
- `ENABLE_CONFIG_VALIDATOR` (default true)
- `ENABLE_METADATA_SELECTION` (experimental)

See docs/configuration.md for the full reference, examples, and best practices.

## Available Tools

- chat, thinkdeep, challenge, planner, consensus
- codereview, precommit, debug, analyze, refactor, tracer, testgen, secaudit, docgen
- listmodels, version

See docs/tools/* for feature details and usage patterns.

## Troubleshooting
- See docs/troubleshooting.md for common issues (environment, MCP wiring, provider setup)
- Enable debug logs: set `LOG_LEVEL=DEBUG` in your environment

## Development
```
pip install -r requirements.txt
pip install -r requirements-dev.txt
ruff check . --fix && black . && isort .
pytest -xvs
```

## License
Apache 2.0 (see LICENSE)

## Acknowledgments
- Model Context Protocol (Anthropic)
- Moonshot/Kimi and ZhipuAI GLM providers
- OpenAI-compatible adapter for custom endpoints and OpenRouter

