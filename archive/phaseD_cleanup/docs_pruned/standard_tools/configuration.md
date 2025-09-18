# Configuration Guide

This guide covers all configuration options for the Zen MCP Server. The server is configured through environment variables defined in your `.env` file.

## Quick Start Configuration

**Auto Mode (Recommended):** Set `DEFAULT_MODEL=auto` and let the MCP choose the best Kimi/GLM model per tool:

```env
# Basic configuration
DEFAULT_MODEL=glm-4.5-flash
KIMI_API_KEY=your-kimi-key
GLM_API_KEY=your-glm-key
```

## Complete Configuration Reference

### Required Configuration

**Workspace Root:**
```env

### API Keys (At least one required)

**Important:** Use EITHER OpenRouter OR native APIs, not both! Having both creates ambiguity about which provider serves each model.

**Option 1: Native APIs (Recommended for direct access)**
```env
# Kimi API (Moonshot)
KIMI_API_KEY=your_kimi_api_key_here
# GLM API (Zhipu)
GLM_API_KEY=your_glm_api_key_here
```

**Option 2: OpenRouter (Access multiple models through one API)**
```env
# OpenRouter for unified model access
OPENROUTER_API_KEY=your_openrouter_api_key_here
# Get from: https://openrouter.ai/
# If using OpenRouter, comment out native API keys above
```

**Option 3: Custom API Endpoints (Local models)**
```env
# For Ollama, vLLM, LM Studio, etc.
CUSTOM_API_URL=http://localhost:11434/v1  # Ollama example
CUSTOM_API_KEY=                                      # Empty for Ollama
CUSTOM_MODEL_NAME=llama3.2                          # Default model
```

**Local Model Connection:**
- Use standard localhost URLs since the server runs natively
- Example: `http://localhost:11434/v1` for Ollama

### Model Configuration

**Default Model Selection:**
```env
# Options: 'auto', 'pro', 'flash', 'o3', 'o3-mini', 'o4-mini', etc.
DEFAULT_MODEL=glm-4.5-flash  # Default to GLM fast model; set 'auto' to let MCP pick
```

**Available Models:**
- **`auto`**: Claude automatically selects the optimal model
- **`pro`** (Gemini 2.5 Pro): Extended thinking, deep analysis
- **`flash`** (Gemini 2.0 Flash): Ultra-fast responses
- **`o3`**: Strong logical reasoning (200K context)
- **`o3-mini`**: Balanced speed/quality (200K context)
- **`o4-mini`**: Latest reasoning model, optimized for shorter contexts
- **`grok-3`**: GROK-3 advanced reasoning (131K context)
- **`grok-4-latest`**: GROK-4 latest flagship model (256K context)
- **Custom models**: via OpenRouter or local APIs

### Thinking Mode Configuration

**Default Thinking Mode for ThinkDeep:**
```env
# Only applies to models supporting extended thinking (e.g., Gemini 2.5 Pro)
DEFAULT_THINKING_MODE_THINKDEEP=high

# Available modes and token consumption:
#   minimal: 128 tokens   - Quick analysis, fastest response
#   low:     2,048 tokens - Light reasoning tasks
#   medium:  8,192 tokens - Balanced reasoning
#   high:    16,384 tokens - Complex analysis (recommended for thinkdeep)
#   max:     32,768 tokens - Maximum reasoning depth
```

### Model Usage Restrictions

Control which models can be used from each provider for cost control, compliance, or standardization:

```env
# Format: Comma-separated list (case-insensitive, whitespace tolerant)
# Empty or unset = all models allowed (default)

# OpenAI model restrictions
OPENAI_ALLOWED_MODELS=o3-mini,o4-mini,mini

# Gemini model restrictions
GOOGLE_ALLOWED_MODELS=flash,pro

# X.AI GROK model restrictions
XAI_ALLOWED_MODELS=grok-3,grok-3-fast,grok-4-latest

# OpenRouter model restrictions (affects models via custom provider)
OPENROUTER_ALLOWED_MODELS=opus,sonnet,mistral
```

**Supported Model Names:**

**OpenAI Models:**
- `o3` (200K context, high reasoning)
- `o3-mini` (200K context, balanced)
- `o4-mini` (200K context, latest balanced)
- `mini` (shorthand for o4-mini)

**Gemini Models:**
- `gemini-2.5-flash` (1M context, fast)
- `gemini-2.5-pro` (1M context, powerful)
- `flash` (shorthand for Flash model)
- `pro` (shorthand for Pro model)

**X.AI GROK Models:**
- `grok-4-latest` (256K context, latest flagship model with reasoning, vision, and structured outputs)
- `grok-3` (131K context, advanced reasoning)
- `grok-3-fast` (131K context, higher performance)
- `grok` (shorthand for grok-4-latest)
- `grok4` (shorthand for grok-4-latest)
- `grok3` (shorthand for grok-3)
- `grokfast` (shorthand for grok-3-fast)

**Example Configurations:**
```env
# Cost control - only cheap models
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=flash

# Single model standardization
OPENAI_ALLOWED_MODELS=o4-mini
GOOGLE_ALLOWED_MODELS=pro

# Balanced selection
GOOGLE_ALLOWED_MODELS=flash,pro
XAI_ALLOWED_MODELS=grok,grok-3-fast
```

### Advanced Configuration

**Custom Model Configuration:**
```env
# Override default location of custom_models.json
CUSTOM_MODELS_CONFIG_PATH=/path/to/your/custom_models.json
```

**Conversation Settings:**
```env
# How long AI-to-AI conversation threads persist in memory (hours)
# Conversations are auto-purged when claude closes its MCP connection or
# when a session is quit / re-launched
CONVERSATION_TIMEOUT_HOURS=5

# Maximum conversation turns (each exchange = 2 turns)
MAX_CONVERSATION_TURNS=20
```

**Logging Configuration:**
```env
# Logging level: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=DEBUG  # Default: shows detailed operational messages
```

## Configuration Examples

### Development Setup
```env
# Development with Kimi/GLM
DEFAULT_MODEL=glm-4.5-flash
KIMI_API_KEY=your-kimi-key
GLM_API_KEY=your-glm-key
LOG_LEVEL=DEBUG
CONVERSATION_TIMEOUT_HOURS=1
```

### Production Setup
```env
# Production with cost controls
DEFAULT_MODEL=glm-4.5-flash
KIMI_API_KEY=your-kimi-key
GLM_API_KEY=your-glm-key
KIMI_ALLOWED_MODELS=kimi-k2-thinking,kimi-k2-turbo-preview
GLM_ALLOWED_MODELS=glm-4.5-air,glm-4.5-flash
LOG_LEVEL=INFO
CONVERSATION_TIMEOUT_HOURS=3
```

### Local Development
```env
# Local models only
DEFAULT_MODEL=llama3.2
CUSTOM_API_URL=http://localhost:11434/v1
CUSTOM_API_KEY=
CUSTOM_MODEL_NAME=llama3.2
LOG_LEVEL=DEBUG
```


### Provider-native Web Search and EX Unified Controls

You can enable provider-native web search and configure EX unified defaults. The capability layer automatically injects the correct tool schema for each provider.

```env
# Provider switches
KIMI_ENABLE_INTERNET_SEARCH=true
GLM_ENABLE_WEB_BROWSING=true

# EX unified defaults
EX_WEBSEARCH_ENABLED=true
EX_WEBSEARCH_DEFAULT_ON=false           # If request.use_websearch is omitted, use this default
EX_WEBSEARCH_MAX_RESULTS=5
EX_WEBSEARCH_LOCALE=en-US
EX_WEBSEARCH_SAFETY_LEVEL=standard
EX_WEBSEARCH_QUERY_TIMEOUT_MS=8000
EX_WEBSEARCH_TOTAL_TIMEOUT_MS=15000
EX_WEBSEARCH_CACHE_TTL_S=300
# Optional domain allow/block lists (comma-separated)
EX_WEBSEARCH_ALLOWED_DOMAINS=
EX_WEBSEARCH_BLOCKED_DOMAINS=
```

Notes:
- Kimi requires function-calling style tools; GLM requires a `web_search` tool object. The adapter handles this.
- Default behavior can be overridden per-request with `use_websearch` in the tool input.

### Tool-call Visibility & Logging

To capture sanitized provider-native tool-call events (e.g., `web_search`) in a JSONL log:

```env
EX_TOOLCALL_LOG_LEVEL=info
EX_TOOLCALL_LOG_PATH=./logs/toolcalls.jsonl   # Set to enable
EX_TOOLCALL_REDACTION=true                    # Redact URLs and long queries (recommended)
```

When enabled, the server appends sanitized JSON lines describing tool-call events (start/end time, provider, tool_name, latency) to the specified file. This can power UI dropdowns or audit logs showing web-search activity and citations.

### OpenRouter Only
```env
# Single API for multiple models
DEFAULT_MODEL=glm-4.5-flash
OPENROUTER_API_KEY=your-openrouter-key
OPENROUTER_ALLOWED_MODELS=opus,sonnet,gpt-4
LOG_LEVEL=INFO
```

## Important Notes

**Local Networking:**
- Use standard localhost URLs for local models
- The server runs as a native Python process

**API Key Priority:**
- Native APIs take priority over OpenRouter when both are configured
- Avoid configuring both native and OpenRouter for the same models

**Model Restrictions:**
- Apply to all usage including auto mode
- Empty/unset = all models allowed
- Invalid model names are warned about at startup

**Configuration Changes:**
- Restart the server with `./run-server.sh` after changing `.env`
- Configuration is loaded once at startup

## Related Documentation

- **[Advanced Usage Guide](advanced-usage.md)** - Advanced model usage patterns, thinking modes, and power user workflows
- **[Context Revival Guide](context-revival.md)** - Conversation persistence and context revival across sessions
- **[AI-to-AI Collaboration Guide](ai-collaboration.md)** - Multi-model coordination and conversation threading