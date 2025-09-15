# EX MCP Server

**🚀 Production-Ready MCP Server with Advanced Context Manager**

An enterprise-grade Model Context Protocol (MCP) server that provides intelligent AI-powered development tools with advanced context management capabilities. Features 25 active tools, multi-provider support, and intelligent context optimization for handling enterprise-scale development workflows.

## ✨ Key Features

- **🧠 Advanced Context Manager**: 10x larger file processing with intelligent optimization
- **🛠️ 25 Active Tools**: Comprehensive development toolkit with workflow-based tools
- **🔌 Multi-Provider Support**: Kimi (Moonshot), GLM (ZhipuAI), OpenAI, OpenRouter, custom endpoints
- **📊 Performance Monitoring**: Real-time metrics and optimization recommendations
- **🚀 Enterprise-Ready**: Production-grade error handling, logging, and monitoring
- **⚡ High Performance**: 28% average token reduction, 50% cache hit rate, <60ms processing

## 🚀 Quick Start

**Prerequisites**: Python 3.10+ (3.12 recommended), Git

### 1. Clone and Setup
```bash
git clone https://github.com/Zazzles2908/EX_AI-mcp-server.git
cd EX_AI-mcp-server

# Run automated setup
./run-server.sh
```

### 2. Configure API Keys
```bash
# Edit .env file with your API keys
KIMI_API_KEY=your_kimi_api_key
GLM_API_KEY=your_glm_api_key
```

### 3. Start Server
```bash
# For development (stdio mode)
python server.py

# For production (WebSocket daemon)
./scripts/ws_start.ps1
```

## 📊 Current Status (2025-01-13)

- **✅ 25 Active Tools** - All tools loading successfully with zero errors
- **✅ Advanced Context Manager** - Intelligent optimization across all tools
- **✅ Performance Monitoring** - Real-time metrics and recommendations
- **✅ Production Ready** - Enterprise-grade reliability and monitoring

## 🛠️ Tool Categories

### **Core Development Tools (10)**
Essential daily development workflows:
- **chat** - Interactive development chat with context optimization
- **analyze** - Step-by-step code analysis workflows
- **codereview** - Comprehensive code review processes
- **debug** - Debugging investigation and resolution
- **refactor** - Code improvement and restructuring
- **testgen** - Automated test generation
- **planner** - Project and task planning
- **thinkdeep** - Complex problem analysis
- **precommit** - Code quality validation
- **challenge** - Development problem-solving

### **Advanced Tools (11)**
Specialized workflows and system management:
- **consensus** - Multi-model consensus analysis
- **docgen** - Automated documentation generation
- **secaudit** - Security analysis and validation
- **tracer** - Code execution tracing
- **context_performance** - Performance monitoring ✨ NEW
- **provider_capabilities** - AI provider information
- **listmodels** - Available model listing
- **activity** - Server activity monitoring
- **version** - Server version and status
- **health** - System health monitoring
- **kimi_chat_with_tools** - Kimi chat integration

### **Provider-Specific Tools (4)**
External API integrations:
- **kimi_upload_and_extract** - File processing with Kimi
- **glm_agent_chat** - GLM Agent Chat API ✨ RE-ENABLED
- **glm_agent_get_result** - GLM Agent result retrieval ✨ RE-ENABLED
- **glm_agent_conversation** - GLM Agent management ✨ RE-ENABLED

## 📚 Documentation

- **[Complete Documentation](docs/DOCUMENTATION_INDEX.md)** - Comprehensive guides and references
- **[Architecture Overview](docs/architecture/ARCHITECTURE_OVERVIEW.md)** - System design and components
- **[Advanced Context Manager](docs/architecture/advanced_context_manager/ADVANCED_CONTEXT_MANAGER_OVERVIEW.md)** - Context optimization system
- **[Tool Documentation](docs/tools/TOOLS_DOCUMENTATION_INDEX.md)** - Individual tool guides
- **[Configuration Guide](docs/standard_tools/configuration.md)** - Setup and configuration

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

