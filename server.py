"""
EX MCP Server - Main server implementation

This module implements the core MCP (Model Context Protocol) server that provides
AI-powered tools for code analysis, review, and assistance using multiple AI models.

The server follows the MCP specification to expose various AI tools as callable functions
that can be used by MCP clients (like Claude). Each tool provides specialized functionality
such as code review, debugging, deep thinking, and general chat capabilities.

Key Components:
- MCP Server: Handles protocol communication and tool discovery
- Tool Registry: Maps tool names to their implementations
- Request Handler: Processes incoming tool calls and returns formatted responses
- Configuration: Manages API keys and model settings

The server runs on stdio (standard input/output) and communicates using JSON-RPC messages
as defined by the MCP protocol.
"""

import asyncio
import atexit
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Optional



# EARLY DIAGNOSTIC (gate via STDERR_BREADCRUMBS to avoid noisy stderr for strict clients)
_DEF = lambda k, d: os.getenv(k, d).strip().lower()
def _env_true(key: str, default: str = "false") -> bool:
    try:
        return os.getenv(key, default).strip().lower() in {"1","true","yes","on"}
    except Exception:
        return False

_stderr_breadcrumbs = lambda: _env_true("STDERR_BREADCRUMBS", "false")
if _stderr_breadcrumbs():
    print("[ex-mcp] bootstrap starting (pid=%s, py=%s)" % (os.getpid(), sys.executable), file=sys.stderr)

# Early error writer to wrapper_error.log for crashes before logging is configured
def _write_wrapper_error(text: str) -> None:
    try:
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        with open(log_dir / "wrapper_error.log", "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception:
        pass

# Try to load environment variables from .env file if dotenv is available
# This is optional - environment variables can still be passed directly
try:
    from dotenv import load_dotenv

    # Load environment variables with precedence:
    # 1) ENV_FILE explicit path if provided
    # 2) .env in the script directory
    script_dir = Path(__file__).parent
    default_env = script_dir / ".env"
    explicit_env = os.getenv("ENV_FILE")
    try:
        if explicit_env and os.path.exists(explicit_env):
            load_dotenv(dotenv_path=explicit_env)
        else:
            load_dotenv(dotenv_path=default_env)
    except Exception as dotenv_err:
        msg = f"[ex-mcp] dotenv load failed: {dotenv_err}"
        print(msg, file=sys.stderr)
        _write_wrapper_error(msg)
except ImportError:
    # dotenv not available - environment variables can still be passed directly
    pass

# Lightweight per-call env hot-reload (opt-in via EX_HOTRELOAD_ENV=true)
# Re-reads ENV_FILE or the default .env and updates os.environ in-place.
# Safe to call frequently; dotenv is fast on small files.
def _hot_reload_env() -> None:
    try:
        from dotenv import load_dotenv as _ld
        path = explicit_env if (explicit_env and os.path.exists(explicit_env)) else default_env
        _ld(dotenv_path=path, override=True)
    except Exception:
        # Never let hot-reload break a tool call
        pass

# Import MCP SDK with protective logging so missing deps are obvious in stderr
try:
    from mcp.server import Server  # noqa: E402
    from mcp.server.models import InitializationOptions  # noqa: E402
    from mcp.server.stdio import stdio_server  # noqa: E402
    from mcp.types import (  # noqa: E402
        GetPromptResult,
        Prompt,
        PromptMessage,
        PromptsCapability,
        ServerCapabilities,
        TextContent,
        Tool,
        ToolsCapability,
    )
except Exception as mcp_import_err:
    print(f"[ex-mcp] MCP import failed: {mcp_import_err}", file=sys.stderr)
    # Re-raise so the client sees process exit, but with stderr breadcrumbs
    raise

# MCP SDK compatibility: ToolAnnotations was added after some releases
try:  # noqa: E402
    from mcp.types import ToolAnnotations  # type: ignore
    MCP_HAS_TOOL_ANNOTATIONS = True
except Exception:  # pragma: no cover
    ToolAnnotations = None  # type: ignore
    MCP_HAS_TOOL_ANNOTATIONS = False

from config import (  # noqa: E402
    DEFAULT_MODEL,
    THINK_ROUTING_ENABLED,
    __version__,
)
from tools import (  # noqa: E402
    AnalyzeTool,
    ChallengeTool,
    ChatTool,
    CodeReviewTool,
    ConsensusTool,
    DebugIssueTool,
    DocgenTool,
    ListModelsTool,
    PlannerTool,
    PrecommitTool,
    RefactorTool,
    SecauditTool,
    TestGenTool,
    ThinkDeepTool,
    TracerTool,
    VersionTool,
)
from tools.models import ToolOutput  # noqa: E402
# Progress helper
from utils.progress import set_mcp_notifier, send_progress, start_progress_capture, get_progress_log  # noqa: E402
# Auggie configuration and wrappers (optional)
AUGGIE_ACTIVE = False
try:
    from auggie.config import load_auggie_config, start_config_watcher, get_auggie_settings
    load_auggie_config()
    start_config_watcher()
    settings = get_auggie_settings() or {}
    AUGGIE_ACTIVE = bool(settings)
    logging.info("Auggie config: loaded and watcher started")
except Exception as _e:
    logging.debug(f"Auggie config not active or failed to initialize: {_e}")

AUGGIE_WRAPPERS_AVAILABLE = False
try:
    from auggie.wrappers import aug_chat as _aug_chat, aug_thinkdeep as _aug_thinkdeep, aug_consensus as _aug_consensus
    AUGGIE_WRAPPERS_AVAILABLE = True
except Exception as _e:
    logging.debug(f"Auggie wrappers not available: {_e}")

# Auto-activation for Auggie CLI usage
import sys as _sys
import os as _os
# Production: prefer JSON logs and INFO by default (overridden via env)


def detect_auggie_cli() -> bool:
    return _os.getenv("AUGGIE_CLI") == "true" or (len(_sys.argv) > 0 and "auggie" in (_sys.argv[0] or ""))


# Configure logging for server operations
# Can be controlled via LOG_LEVEL environment variable (DEBUG, INFO, WARNING, ERROR)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Create timezone-aware formatter


class LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        """Override to use local timezone instead of UTC"""
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = f"{t},{record.msecs:03.0f}"
        return s


# Configure both console and file logging
log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Optional JSON logging (structured)
class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        import json as _json
        # Build a compact structured payload
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Include extras when present
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return _json.dumps(payload, ensure_ascii=False)

use_json_logs = os.getenv("LOG_FORMAT", "json").lower() in {"json", "structured", "jsonl"}

# Clear any existing handlers first
root_logger = logging.getLogger()
root_logger.handlers.clear()

# Create and configure stderr handler explicitly
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(getattr(logging, log_level, logging.INFO))
stderr_handler.setFormatter(JsonLineFormatter() if use_json_logs else LocalTimeFormatter(log_format))
root_logger.addHandler(stderr_handler)

# Note: MCP stdio_server interferes with stderr during tool execution
# All logs are properly written to logs/mcp_server.log for monitoring

# Set root logger level
root_logger.setLevel(getattr(logging, log_level, logging.INFO))

# Add rotating file handler for local log monitoring

try:
    # Create logs directory in project root
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Main server log with size-based rotation (20MB max per file)
    # This ensures logs don't grow indefinitely and are properly managed
    file_handler = RotatingFileHandler(
        log_dir / "mcp_server.log",
        maxBytes=20 * 1024 * 1024,  # 20MB max file size
        backupCount=5,  # Keep 10 rotated files (100MB total)
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    file_handler.setFormatter(LocalTimeFormatter(log_format))
    logging.getLogger().addHandler(file_handler)

    # Note: We consolidate logging to the root file log and stderr; activity logs propagate to root.
    mcp_logger = logging.getLogger("mcp_activity")
    # Honor ACTIVITY_LOG flag (default true). When false, disable this logger to avoid writes.
    if not _env_true("ACTIVITY_LOG", "true"):
        mcp_logger.disabled = True
    else:
        mcp_logger.setLevel(logging.INFO)
        mcp_logger.propagate = True

    # Add dedicated activity file handler for tool activity dropdowns (optional path override)
    try:
        activity_path = os.getenv("ACTIVITY_LOG_FILE", str(log_dir / "mcp_activity.log"))
        activity_handler = RotatingFileHandler(
            activity_path,
            maxBytes=20 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        activity_handler.setLevel(logging.INFO)
        activity_handler.setFormatter(LocalTimeFormatter(log_format))
        mcp_logger.addHandler(activity_handler)
        logging.info(f"Activity logging to: {activity_path}")
    except Exception as e:
        logging.warning(f"Could not set up activity log file: {e}")


        # Dedicated ERROR+ rotating file handler for centralized error tracking
        try:
            errors_handler = RotatingFileHandler(
                log_dir / "mcp_errors.log",
                maxBytes=10 * 1024 * 1024,  # 10MB max per file
                backupCount=5,
                encoding="utf-8",
            )
            errors_handler.setLevel(logging.ERROR)
            errors_handler.setFormatter(LocalTimeFormatter(log_format))
            logging.getLogger().addHandler(errors_handler)
            logging.info("Centralized error log enabled at: %s", str(log_dir / "mcp_errors.log"))
        except Exception as e:
            logging.warning(f"Could not set up centralized error log: {e}")

    # Log setup info directly to root logger since logger isn't defined yet
    logging.info(f"Logging to: {log_dir / 'mcp_server.log'}")
    logging.info(f"Process PID: {os.getpid()}")

except Exception as e:
    print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

logger = logging.getLogger(__name__)


# Create the MCP server instance with a unique name identifier
# This name is used by MCP clients to identify and connect to this specific server
server: Server = Server(os.getenv("MCP_SERVER_ID", "ex-server"))

# Optional dispatcher wiring (P2 scaffolding) — env-gated and non‑operational by default
USE_DISPATCHER = os.getenv("EX_USE_DISPATCHER", "false").strip().lower() in {"1","true","yes","on"}
try:
    from src.server.dispatcher import Dispatcher  # type: ignore
    _dispatcher = Dispatcher() if USE_DISPATCHER else None
    if _dispatcher:
        logger.info("Dispatcher initialized (scaffold) — no routing changes yet")
except Exception as _disp_err:
    _dispatcher = None
    logger.debug(f"Dispatcher not active: {_disp_err}")

# Optional AI Manager wiring (P4 scaffolding) — env-gated and non‑operational by default
AI_MANAGER_ENABLED = os.getenv("EX_AI_MANAGER_ENABLED", "false").strip().lower() in {"1","true","yes","on"}
AI_MANAGER_ROUTE = os.getenv("EX_AI_MANAGER_ROUTE", "false").strip().lower() in {"1","true","yes","on"}

try:
    from src.managers.ai_manager import AiManager  # type: ignore
    _ai_manager = AiManager(enabled=AI_MANAGER_ENABLED)
    if _ai_manager and _ai_manager.enabled:
        logger.info("AI Manager initialized (scaffold) — no routing changes yet")
except Exception as _aim_err:  # pragma: no cover
    _ai_manager = None
    logger.debug(f"AI Manager not active: {_aim_err}")

# P2 scaffolding: Telemetry and RegistryBridge touchpoints (no behavior change)
try:
    from src.server.telemetry import telemetry as _telemetry  # type: ignore
except Exception as _t_err:  # pragma: no cover
    _telemetry = None
    logger.debug(f"Telemetry not active: {_t_err}")
try:
    from src.server.registry_bridge import registry_bridge as _registry_bridge  # type: ignore
except Exception as _r_err:  # pragma: no cover
    _registry_bridge = None
    logger.debug(f"RegistryBridge not active: {_r_err}")

if _telemetry:
    logger.info("Telemetry touchpoint initialized (no-op)")
if _registry_bridge:
    try:
        _probe_models = _registry_bridge.get_available_models()
        logger.debug(f"RegistryBridge probe: models={len(_probe_models)}")
    except Exception as _probe_err:  # pragma: no cover
        logger.debug(f"RegistryBridge probe failed: {_probe_err}")


# Optional System Cleanup modules (import-safe; no behavior change)
try:
    from src.server.response_handler import ResponseHandler as _ResponseHandler  # type: ignore
    _response_handler = _ResponseHandler()
    logger.info("ResponseHandler initialized (import-safe; no-op integration)")
except Exception as _rh_err:  # pragma: no cover
    _response_handler = None
    logger.debug(f"ResponseHandler not active: {_rh_err}")

try:
    from src.server.model_resolver import ModelResolver as _ModelResolver  # type: ignore
    _model_resolver = _ModelResolver()
    logger.info("ModelResolver initialized (import-safe; no-op integration)")
except Exception as _mr_err:  # pragma: no cover
    _model_resolver = None
    logger.debug(f"ModelResolver not active: {_mr_err}")

try:
    from src.server.mcp_protocol import ensure_messages as _ensure_messages  # type: ignore
    logger.debug("MCP protocol utils loaded (ensure_messages available)")
except Exception as _mp_err:  # pragma: no cover
    logger.debug(f"MCP protocol utils not loaded: {_mp_err}")

# Constants for tool filtering
ESSENTIAL_TOOLS = {"version", "listmodels"}


def parse_disabled_tools_env() -> set[str]:
    """
    Parse the DISABLED_TOOLS environment variable into a set of tool names.

    Returns:
        Set of lowercase tool names to disable, empty set if none specified
    """
    disabled_tools_env = os.getenv("DISABLED_TOOLS", "").strip()
    if not disabled_tools_env:
        return set()
    return {t.strip().lower() for t in disabled_tools_env.split(",") if t.strip()}


def validate_disabled_tools(disabled_tools: set[str], all_tools: dict[str, Any]) -> None:
    """
    Validate the disabled tools list and log appropriate warnings.

    Args:
        disabled_tools: Set of tool names requested to be disabled
        all_tools: Dictionary of all available tool instances
    """
    essential_disabled = disabled_tools & ESSENTIAL_TOOLS
    if essential_disabled:
        logger.warning(f"Cannot disable essential tools: {sorted(essential_disabled)}")
    unknown_tools = disabled_tools - set(all_tools.keys())
    if unknown_tools:
        logger.warning(f"Unknown tools in DISABLED_TOOLS: {sorted(unknown_tools)}")


def apply_tool_filter(all_tools: dict[str, Any], disabled_tools: set[str]) -> dict[str, Any]:
    """
    Apply the disabled tools filter to create the final tools dictionary.

    Args:
        all_tools: Dictionary of all available tool instances
        disabled_tools: Set of tool names to disable

    Returns:
        Dictionary containing only enabled tools
    """
    enabled_tools = {}
    for tool_name, tool_instance in all_tools.items():
        if tool_name in ESSENTIAL_TOOLS or tool_name not in disabled_tools:
            enabled_tools[tool_name] = tool_instance
        else:
            logger.debug(f"Tool '{tool_name}' disabled via DISABLED_TOOLS")
    return enabled_tools


def log_tool_configuration(disabled_tools: set[str], enabled_tools: dict[str, Any]) -> None:
    """
    Log the final tool configuration for visibility.

    Args:
        disabled_tools: Set of tool names that were requested to be disabled
        enabled_tools: Dictionary of tools that remain enabled
    """
    if not disabled_tools:
        logger.info("All tools enabled (DISABLED_TOOLS not set)")
        return
    actual_disabled = disabled_tools - ESSENTIAL_TOOLS
    if actual_disabled:
        logger.debug(f"Disabled tools: {sorted(actual_disabled)}")
        logger.info(f"Active tools: {sorted(enabled_tools.keys())}")


def filter_disabled_tools(all_tools: dict[str, Any]) -> dict[str, Any]:
    """
    Filter tools based on DISABLED_TOOLS environment variable.

    Args:
        all_tools: Dictionary of all available tool instances

    Returns:
        dict: Filtered dictionary containing only enabled tools
    """
    disabled_tools = parse_disabled_tools_env()
    if not disabled_tools:
        log_tool_configuration(disabled_tools, all_tools)
        return all_tools
    validate_disabled_tools(disabled_tools, all_tools)
    enabled_tools = apply_tool_filter(all_tools, disabled_tools)
    log_tool_configuration(disabled_tools, enabled_tools)
    return enabled_tools


# Initialize the tool registry with all available AI-powered tools
# Each tool provides specialized functionality for different development tasks
# Tools are instantiated once and reused across requests (stateless design)
TOOLS = {
    "chat": ChatTool(),  # Interactive development chat and brainstorming
    "thinkdeep": ThinkDeepTool(),  # Step-by-step deep thinking workflow with expert analysis
    "planner": PlannerTool(),  # Interactive sequential planner using workflow architecture
    "consensus": ConsensusTool(),  # Step-by-step consensus workflow with multi-model analysis
    "codereview": CodeReviewTool(),  # Comprehensive step-by-step code review workflow with expert analysis
    "precommit": PrecommitTool(),  # Step-by-step pre-commit validation workflow

    "debug": DebugIssueTool(),  # Root cause analysis and debugging assistance
    "secaudit": SecauditTool(),  # Comprehensive security audit with OWASP Top 10 and compliance coverage
    "docgen": DocgenTool(),  # Step-by-step documentation generation with complexity analysis
    "analyze": AnalyzeTool(),  # General-purpose file and code analysis
    "refactor": RefactorTool(),  # Step-by-step refactoring analysis workflow with expert validation
    "tracer": TracerTool(),  # Static call path prediction and control flow analysis
    "testgen": TestGenTool(),  # Step-by-step test generation workflow with expert validation
    "challenge": ChallengeTool(),  # Critical challenge prompt wrapper to avoid automatic agreement
    "listmodels": ListModelsTool(),  # List all available AI models by provider
    "version": VersionTool(),  # Display server version and system information
}

# Optionally register Auggie-optimized tools (aug_*) in addition to originals
if (AUGGIE_ACTIVE or detect_auggie_cli()) and AUGGIE_WRAPPERS_AVAILABLE:
    logger.info("Registering Auggie-optimized tools (aug_*) alongside originals")

    class AugChatTool(ChatTool):
        def get_name(self) -> str: return "aug_chat"
        def get_description(self) -> str:
            return "AUGGIE CHAT (CLI-optimized): Structured output, progress, and fallback-aware routing"
        async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
            # Map schema: reuse Chat schema; pass through to wrapper
            out = await _aug_chat(arguments)
            return [TextContent(type="text", text=out)]

    class AugThinkDeepTool(ThinkDeepTool):
        def get_name(self) -> str: return "aug_thinkdeep"
        def get_description(self) -> str:
            return "AUGGIE THINKDEEP (CLI-optimized): Progress indicators and robust fallback"
        async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
            out = await _aug_thinkdeep(arguments)
            return [TextContent(type="text", text=out)]

    class AugConsensusTool(ConsensusTool):
        def get_name(self) -> str: return "aug_consensus"
        def get_description(self) -> str:
            return "AUGGIE CONSENSUS (CLI-optimized): Side-by-side compare and synthesis"
        async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
            out = await _aug_consensus(arguments)
            return [TextContent(type="text", text=out)]

    # Only expose Auggie wrappers in explicit CLI sessions and when allowed
    if detect_auggie_cli() and _env_true("ALLOW_AUGGIE", "false"):
        TOOLS.update({
            "aug_chat": AugChatTool(),
            "aug_thinkdeep": AugThinkDeepTool(),
            "aug_consensus": AugConsensusTool(),
        })

# Build tools with lean gating (LEAN_MODE/LEAN_TOOLS/DISABLED_TOOLS)
try:
    from tools.registry import ToolRegistry
    _tool_registry = ToolRegistry()
    _tool_registry.build_tools()
    TOOLS = _tool_registry.list_tools()
    logger.info(f"Lean tool registry active - tools: {sorted(TOOLS.keys())}")
    try:
        # Native provider stubs (not wired)
        if os.getenv("ENABLE_ZHIPU_NATIVE", "false").strip().lower() in {"1","true","yes","on"}:
            try:
                from src.providers.zhipu_native import ZhipuNativeProvider  # type: ignore
                logger.info("Zhipu native provider stub enabled (not wired)")
            except Exception as _zp_err:
                logger.debug(f"Zhipu stub load skipped: {_zp_err}")
        if os.getenv("ENABLE_MOONSHOT_NATIVE", "false").strip().lower() in {"1","true","yes","on"}:
            try:
                from src.providers.moonshot_native import MoonshotNativeProvider  # type: ignore
                logger.info("Moonshot native provider stub enabled (not wired)")
            except Exception as _ms_err:
                logger.debug(f"Moonshot stub load skipped: {_ms_err}")
    except Exception as _opts_err:
        logger.debug(f"Optional tool/provider registration skipped: {_opts_err}")


except Exception as e:
    logger.warning(f"Lean tool registry unavailable, falling back to static tool set: {e}")

# Re-register Auggie wrappers after lean registry build if applicable
try:
    if 'AugChatTool' in globals() and detect_auggie_cli() and _env_true("ALLOW_AUGGIE", "false"):
        logger.info("Re-registering Auggie-optimized tools (aug_*) after registry build")
        TOOLS.update({
            "aug_chat": AugChatTool(),
            "aug_thinkdeep": AugThinkDeepTool(),
            "aug_consensus": AugConsensusTool(),
        })
except Exception as e:
    logger.debug(f"Auggie wrapper re-registration skipped/failed: {e}")
    # Enforce exact production toolset allowlist (16 tools) during fallback
    EXACT_TOOLSET = {
        "chat","analyze","debug","codereview","refactor","secaudit","planner","tracer",
        "testgen","consensus","thinkdeep","docgen","version","listmodels","precommit","challenge",
        # Extended provider capabilities (Kimi/GLM) ensured under fallback
        "kimi_upload_and_extract","kimi_multi_file_chat","kimi_chat_with_tools",
        "glm_upload_file","glm_multi_file_chat","glm_agent_chat","glm_agent_get_result","glm_agent_conversation"
    }
    # Filter to allowlist first, then apply DISABLED_TOOLS policy
    TOOLS = {k: v for k, v in TOOLS.items() if k in EXACT_TOOLSET}
    TOOLS = filter_disabled_tools(TOOLS)
    if _env_true("POLICY_EXACT_TOOLSET", "true"):
        expected = len(EXACT_TOOLSET)
        if len(TOOLS) != expected:
            logger.error(f"POLICY_EXACT_TOOLSET violation: have {len(TOOLS)} tools (expected {expected}): {sorted(TOOLS.keys())}")

# Rich prompt templates for all tools
PROMPT_TEMPLATES = {
    "chat": {
        "name": "chat",
        "description": "Chat and brainstorm ideas",
        "template": "Chat with {model} about this",
    },
    "thinkdeep": {
        "name": "thinkdeeper",
        "description": "Step-by-step deep thinking workflow with expert analysis",
        "template": "Start comprehensive deep thinking workflow with {model} using {thinking_mode} thinking mode",
    },
    "planner": {
        "name": "planner",
        "description": "Break down complex ideas, problems, or projects into multiple manageable steps",
        "template": "Create a detailed plan with {model}",
    },
    "consensus": {
        "name": "consensus",
        "description": "Step-by-step consensus workflow with multi-model analysis",
        "template": "Start comprehensive consensus workflow with {model}",
    },
    "codereview": {
        "name": "review",
        "description": "Perform a comprehensive code review",
        "template": "Perform a comprehensive code review with {model}",
    },
    "precommit": {
        "name": "precommit",
        "description": "Step-by-step pre-commit validation workflow",
        "template": "Start comprehensive pre-commit validation workflow with {model}",
    },
    "debug": {
        "name": "debug",
        "description": "Debug an issue or error",
        "template": "Help debug this issue with {model}",
    },
    "secaudit": {
        "name": "secaudit",
        "description": "Comprehensive security audit with OWASP Top 10 coverage",
        "template": "Perform comprehensive security audit with {model}",
    },
    "docgen": {
        "name": "docgen",
        "description": "Generate comprehensive code documentation with complexity analysis",
        "template": "Generate comprehensive documentation with {model}",
    },
    "analyze": {
        "name": "analyze",
        "description": "Analyze files and code structure",
        "template": "Analyze these files with {model}",
    },
    "refactor": {
        "name": "refactor",
        "description": "Refactor and improve code structure",
        "template": "Refactor this code with {model}",
    },
    "tracer": {
        "name": "tracer",
        "description": "Trace code execution paths",
        "template": "Generate tracer analysis with {model}",
    },
    "testgen": {
        "name": "testgen",
        "description": "Generate comprehensive tests",
        "template": "Generate comprehensive tests with {model}",
    },
    "challenge": {
        "name": "challenge",
        "description": "Challenge a statement critically without automatic agreement",
        "template": "Challenge this statement critically",
    },
    "listmodels": {
        "name": "listmodels",
        "description": "List available AI models",
        "template": "List all available models",
    },
    "version": {
        "name": "version",
        "description": "Show server version and system information",
        "template": "Show EX MCP Server version",
    },
}


def configure_providers():
    """
    Configure and validate AI providers based on available API keys.

    This function checks for API keys and registers the appropriate providers.
    At least one valid API key (Kimi or GLM) is required.

    Raises:
        ValueError: If no valid API keys are found or conflicting configurations detected
    """
    # Log environment variable status for debugging
    logger.debug("Checking environment variables for API keys...")
    api_keys_to_check = ["KIMI_API_KEY", "GLM_API_KEY", "OPENROUTER_API_KEY", "CUSTOM_API_URL"]
    for key in api_keys_to_check:
        value = os.getenv(key)
        logger.debug(f"  {key}: {'[PRESENT]' if value else '[MISSING]'}")

    # Optional explicit provider gating (comma-separated names matching ProviderType)
    disabled_providers = {p.strip().upper() for p in os.getenv("DISABLED_PROVIDERS", "").split(",") if p.strip()}
    allowed_providers = {p.strip().upper() for p in os.getenv("ALLOWED_PROVIDERS", "").split(",") if p.strip()}

    from src.providers import ModelProviderRegistry
    from src.providers.base import ProviderType
    from src.providers.custom import CustomProvider
    from utils.model_restrictions import get_restriction_service

    # Import provider classes lazily to avoid optional dependency import errors
    OpenAIModelProvider = None
    GeminiModelProvider = None
    XAIModelProvider = None
    KimiModelProvider = None
    GLMModelProvider = None
    OpenRouterProvider = None
    DIALModelProvider = None

    # Force-disable providers we don't support in this deployment
    disabled_providers.update({"GOOGLE", "OPENAI", "XAI", "DIAL"})

    valid_providers = []
    has_native_apis = False
    has_openrouter = False
    has_custom = False

    # Gemini disabled by policy
    gemini_key = os.getenv("GEMINI_API_KEY")

    # OpenAI disabled by policy
    openai_key = os.getenv("OPENAI_API_KEY")
    logger.debug(f"OpenAI key check: key={'[PRESENT]' if openai_key else '[MISSING]'}")

    # X.AI disabled by policy
    xai_key = os.getenv("XAI_API_KEY")

    # DIAL disabled by policy
    dial_key = os.getenv("DIAL_API_KEY")

    # Check for Kimi API key (accept vendor alias)
    kimi_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
    if kimi_key and kimi_key != "your_kimi_api_key_here" and "KIMI" not in disabled_providers and (not allowed_providers or "KIMI" in allowed_providers):
        try:
            from src.providers.kimi import KimiModelProvider as _Kimi
            KimiModelProvider = _Kimi  # type: ignore
            valid_providers.append("Kimi")
            has_native_apis = True
            logger.info("Kimi API key found - Moonshot AI models available")
        except Exception:
            logger.warning("Kimi provider import failed; continuing without Kimi")

    # Check for GLM API key (accept vendor alias)
    glm_key = os.getenv("GLM_API_KEY") or os.getenv("ZHIPUAI_API_KEY")
    if glm_key and glm_key != "your_glm_api_key_here" and "GLM" not in disabled_providers and (not allowed_providers or "GLM" in allowed_providers):
        try:
            from src.providers.glm import GLMModelProvider as _GLM
            GLMModelProvider = _GLM  # type: ignore
            valid_providers.append("GLM")
            has_native_apis = True
            logger.info("GLM API key found - ZhipuAI models available")
        except Exception:
            logger.warning("GLM provider import failed; continuing without GLM")

    # Check for OpenRouter API key
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    logger.debug(f"OpenRouter key check: key={'[PRESENT]' if openrouter_key else '[MISSING]'}")
    if openrouter_key and openrouter_key != "your_openrouter_api_key_here":
        valid_providers.append("OpenRouter")
        has_openrouter = True
        logger.info("OpenRouter API key found - Multiple models available via OpenRouter")
    else:
        if not openrouter_key:
            logger.debug("OpenRouter API key not found in environment")
        else:
            logger.debug("OpenRouter API key is placeholder value")

    # Check for custom API endpoint (Ollama, vLLM, etc.)
    custom_url = os.getenv("CUSTOM_API_URL")
    if custom_url:
        # IMPORTANT: Always read CUSTOM_API_KEY even if empty
        # - Some providers (vLLM, LM Studio, enterprise APIs) require authentication
        # - Others (Ollama) work without authentication (empty key)
        # - DO NOT remove this variable - it's needed for provider factory function
        custom_key = os.getenv("CUSTOM_API_KEY", "")  # Default to empty (Ollama doesn't need auth)
        custom_model = os.getenv("CUSTOM_MODEL_NAME", "llama3.2")
        valid_providers.append(f"Custom API ({custom_url})")
        has_custom = True
        logger.info(f"Custom API endpoint found: {custom_url} with model {custom_model}")
        if custom_key:
            logger.debug("Custom API key provided for authentication")
        else:
            logger.debug("No custom API key provided (using unauthenticated access)")

    # Register providers in priority order:
    # 1. Native APIs first (most direct and efficient)
    if has_native_apis:
        if kimi_key and kimi_key != "your_kimi_api_key_here" and "KIMI" not in disabled_providers:
            ModelProviderRegistry.register_provider(ProviderType.KIMI, KimiModelProvider)
        if glm_key and glm_key != "your_glm_api_key_here" and "GLM" not in disabled_providers:
            ModelProviderRegistry.register_provider(ProviderType.GLM, GLMModelProvider)

    # 2. Custom provider second (for local/private models)
    if has_custom and "CUSTOM" not in disabled_providers:
        # Factory function that creates CustomProvider with proper parameters
        def custom_provider_factory(api_key=None):
            # api_key is CUSTOM_API_KEY (can be empty for Ollama), base_url from CUSTOM_API_URL
            base_url = os.getenv("CUSTOM_API_URL", "")
            return CustomProvider(api_key=api_key or "", base_url=base_url)  # Use provided API key or empty string

        ModelProviderRegistry.register_provider(ProviderType.CUSTOM, custom_provider_factory)

    # 3. OpenRouter last (catch-all for everything else)
    if has_openrouter and "OPENROUTER" not in disabled_providers:
        ModelProviderRegistry.register_provider(ProviderType.OPENROUTER, OpenRouterProvider)

    # Require at least one valid provider
    if not valid_providers:
        raise ValueError(
            "At least one API configuration is required. Please set either:\n"
            "- KIMI_API_KEY for Moonshot Kimi models\n"
            "- GLM_API_KEY for ZhipuAI GLM models\n"
            "- OPENROUTER_API_KEY for OpenRouter (multiple models)\n"
            "- CUSTOM_API_URL for local models (Ollama, vLLM, etc.)"
        )

    logger.info(f"Available providers: {', '.join(valid_providers)}")
    # Diagnostic: summarize configured providers and model counts for quick visibility
    try:
        with_keys = [p.name for p in ModelProviderRegistry.get_available_providers_with_keys()]
        glm_models = ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.GLM)
        kimi_models = ModelProviderRegistry.get_available_model_names(provider_type=ProviderType.KIMI)
        logger.info(
            "Providers configured: %s; GLM models: %d; Kimi models: %d",
            ", ".join(with_keys) if with_keys else "none",
            len(glm_models),
            len(kimi_models),
        )
    except Exception as _e:
        logger.debug(f"Provider availability summary skipped: {_e}")


    # Log provider priority
    priority_info = []
    if has_native_apis:
        priority_info.append("Native APIs (Gemini, OpenAI)")
    if has_custom:
        priority_info.append("Custom endpoints")
    if has_openrouter:
        priority_info.append("OpenRouter (catch-all)")

    if len(priority_info) > 1:
        logger.info(f"Provider priority: {' â†’ '.join(priority_info)}")

    # Register cleanup function for providers
    def cleanup_providers():
        """Clean up all registered providers on shutdown."""
        try:
            registry = ModelProviderRegistry()
            if hasattr(registry, "_initialized_providers"):
                for provider in list(registry._initialized_providers.items()):
                    try:
                        if provider and hasattr(provider, "close"):
                            provider.close()
                    except Exception:
                        # Logger might be closed during shutdown
                        pass
        except Exception:
            # Silently ignore any errors during cleanup
            pass

    atexit.register(cleanup_providers)

    # Check and log model restrictions
    restriction_service = get_restriction_service()
    restrictions = restriction_service.get_restriction_summary()

    if restrictions:
        logger.info("Model restrictions configured:")
        for provider_name, allowed_models in restrictions.items():
            if isinstance(allowed_models, list):
                logger.info(f"  {provider_name}: {', '.join(allowed_models)}")
            else:
                logger.info(f"  {provider_name}: {allowed_models}")

        # Validate restrictions against known models
        provider_instances = {}
        provider_types_to_validate = [
            ProviderType.KIMI,
            ProviderType.GLM,
            ProviderType.CUSTOM,
            ProviderType.OPENROUTER,
        ]
        for provider_type in provider_types_to_validate:
            provider = ModelProviderRegistry.get_provider(provider_type)
            if provider:
                provider_instances[provider_type] = provider

        if provider_instances:
            restriction_service.validate_against_known_models(provider_instances)
    else:
        logger.info("No model restrictions configured - all models allowed")

    # Check if auto mode has any models available after restrictions
    from config import IS_AUTO_MODE

    if IS_AUTO_MODE:
        available_models = ModelProviderRegistry.get_available_models(respect_restrictions=True)
        if not available_models:
            logger.error(
                "Auto mode is enabled but no models are available after applying restrictions. "
                "Please check your OPENAI_ALLOWED_MODELS and GOOGLE_ALLOWED_MODELS settings."
            )
            raise ValueError(
                "No models available for auto mode due to restrictions. "
                "Please adjust your allowed model settings or disable auto mode."
            )


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """
    List all available tools with their descriptions and input schemas.

    This handler is called by MCP clients during initialization to discover
    what tools are available. Each tool provides:
    - name: Unique identifier for the tool
    - description: Detailed explanation of what the tool does
    - inputSchema: JSON Schema defining the expected parameters

    Returns:
        List of Tool objects representing all available tools
    """
    logger.debug("MCP client requested tool list")

    # Try to log client info if available (this happens early in the handshake)
    try:
        from utils.client_info import format_client_info, get_client_info_from_context

        client_info = get_client_info_from_context(server)
        if client_info:
            formatted = format_client_info(client_info)
            logger.info(f"MCP Client Connected: {formatted}")

            # Log to activity file as well
            try:
                mcp_activity_logger = logging.getLogger("mcp_activity")
                friendly_name = client_info.get("friendly_name", "Claude")
                raw_name = client_info.get("name", "Unknown")
                version = client_info.get("version", "Unknown")
                mcp_activity_logger.info(f"MCP_CLIENT_INFO: {friendly_name} (raw={raw_name} v{version})")
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"Could not log client info during list_tools: {e}")
    tools = []

    # Client-aware allow/deny filtering (generic profile with legacy CLAUDE_* fallback)
    try:
        from utils.client_info import get_client_info_from_context
        ci = get_client_info_from_context(server) or {}
        client_name = (ci.get("friendly_name") or ci.get("name") or "").lower()
        # Generic env first, then legacy Claude-specific variables
        raw_allow = os.getenv("CLIENT_TOOL_ALLOWLIST", os.getenv("CLAUDE_TOOL_ALLOWLIST", ""))
        raw_deny  = os.getenv("CLIENT_TOOL_DENYLIST",  os.getenv("CLAUDE_TOOL_DENYLIST",  ""))
        allowlist = {t.strip().lower() for t in raw_allow.split(",") if t.strip()}
        denylist  = {t.strip().lower() for t in raw_deny.split(",") if t.strip()}
    except Exception:
        client_name = ""
        allowlist = set()
        denylist = set()

    # Add all registered AI-powered tools from the TOOLS registry
    for tool in TOOLS.values():
        # Apply optional allow/deny lists generically
        nm = tool.name.lower()
        if allowlist and nm not in allowlist:
            continue
        if denylist and nm in denylist:
            continue

        # Get optional annotations from the tool (env-gated)
        annotations = tool.get_annotations()
        tool_annotations = ToolAnnotations(**annotations) if (annotations and MCP_HAS_TOOL_ANNOTATIONS) else None
        if _env_true("DISABLE_TOOL_ANNOTATIONS", "false"):
            tool_annotations = None

        # Build input schema (optionally slim for heavy tools when explicitly enabled)
        schema = tool.get_input_schema()
        try:
            if _env_true("SLIM_SCHEMAS", "false"):
                if tool.name in {"thinkdeep", "analyze", "consensus"}:
                    schema = {"type": "object", "properties": {}, "additionalProperties": True}
        except Exception:
            pass

        kwargs = dict(
            name=tool.name,
            description=tool.description,
            inputSchema=schema,
        )
        # Only pass annotations if supported by current MCP SDK
        if tool_annotations is not None:
            kwargs["annotations"] = tool_annotations

        tools.append(Tool(**kwargs))

    # Log cache efficiency info
    if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
        logger.debug("OpenRouter registry cache used efficiently across all tool schemas")

    logger.debug(f"Returning {len(tools)} tools to MCP client")
    return tools


# Optional module-level override for tests; monkeypatchable in pytest
_resolve_auto_model = None
# Lazy provider configuration guard for internal tool calls (e.g., audit script)
_providers_configured = False

def _ensure_providers_configured():
    global _providers_configured
    if not _providers_configured:
        try:
            configure_providers()
            _providers_configured = True
        except Exception as e:
            logger.warning(f"Provider configuration failed: {e}")

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # Ensure providers are configured when server is used as a module (tests/audits)
    try:
        _ensure_providers_configured()
    except Exception:
        pass
    import uuid as _uuid
    req_id = str(_uuid.uuid4())
    # Telemetry DRY-RUN (no behavior change)
    try:
        if _telemetry:
            _telemetry.record_event("tool_call_start", name=name, req_id=req_id)
    except Exception:
        pass

    # AI Manager DRY-RUN advisory plan (no behavior change)
    try:
        if _ai_manager and _ai_manager.enabled:
            _plan = _ai_manager.plan_or_route(name, arguments or {})
            if _plan:
                try:
                    logging.getLogger("mcp_activity").info({
                        "event": "ai_manager_plan",
                        "tool": name,
                        "req_id": req_id,
                        "plan": _plan,
                    })
                except Exception:
                    pass
    except Exception as _aim_dry_err:
        logger.debug(f"[AI-MANAGER-DRYRUN] skip: {_aim_dry_err}")

    # AI Manager operational routing (env-gated)
    try:
        if _ai_manager and _ai_manager.enabled and 'AI_MANAGER_ROUTE' in globals() and AI_MANAGER_ROUTE:
            if '_plan' in locals() and _plan:
                _mapped = name
                _prov = (_plan or {}).get("suggested_provider")
                _has_files = bool((_plan or {}).get("has_files"))
                _suggested_model = (_plan or {}).get("suggested_model")
                # Map to tool (provider-aware)
                if _prov == "kimi" and _has_files and isinstance(arguments, dict) and "files" in arguments and "kimi_multi_file_chat" in TOOLS:
                    _mapped = "kimi_multi_file_chat"
                elif _prov == "glm" and "chat" in TOOLS:
                    _mapped = "chat"

                # Inject model hint if not explicitly provided
                if _suggested_model and isinstance(arguments, dict) and "model" not in arguments:
                    arguments["model"] = _suggested_model

                # Provider-specific guard & argument shim when remapping to 'chat'
                if _mapped != name and _mapped in TOOLS:
                    try:
                        # If crossing from provider-specific tool to generic 'chat', translate arguments
                        _from = (name or "").lower()
                        _to = ( _mapped or "" ).lower()
                        _prov_specific = {"kimi_chat_with_tools", "kimi_multi_file_chat", "glm_multi_file_chat", "glm_agent_chat"}

                        def _extract_prompt_from_args(_args: dict[str, Any]) -> str:
                            try:
                                p = str((_args or {}).get("prompt") or "").strip()
                                if p:
                                    return p
                                msgs = (_args or {}).get("messages") or []
                                if isinstance(msgs, list) and msgs:
                                    # pick last user/system content with text
                                    for _m in reversed(msgs):
                                        if isinstance(_m, dict) and str(_m.get("role", "")).lower() in {"user", "system"}:
                                            c = _m.get("content")
                                            if isinstance(c, str) and c.strip():
                                                return c.strip()
                            except Exception:
                                pass
                            return ""

                        if _to == "chat" and _from in _prov_specific:
                            _prompt = _extract_prompt_from_args(arguments if isinstance(arguments, dict) else {})
                            if not _prompt:
                                # Block route when we cannot safely translate arguments
                                try:
                                    logging.getLogger("mcp_activity").info({
                                        "event": "ai_manager_route_blocked",
                                        "from": name,
                                        "to": _mapped,
                                        "req_id": req_id,
                                        "reason": "no_prompt_or_messages_to_translate"
                                    })
                                except Exception:
                                    pass
                            else:
                                # Build translated arguments for ChatTool
                                _chat_args = {"prompt": _prompt}
                                try:
                                    if isinstance(arguments, dict):
                                        # Preserve model and files if present
                                        if "model" in arguments:
                                            _chat_args["model"] = arguments["model"]
                                        if "files" in arguments:
                                            _chat_args["files"] = arguments["files"]
                                except Exception:
                                    pass
                                arguments = _chat_args  # safe shim for chat schema

                        # Log and apply route
                        logging.getLogger("mcp_activity").info({
                            "event": "ai_manager_route",
                            "from": name,
                            "to": _mapped,
                            "req_id": req_id,
                            "note": "operational route (env-gated)"
                        })
                        name = _mapped
                    except Exception:
                        pass
    except Exception as _aim_route_err:
        logger.debug(f"[AI-MANAGER-ROUTE] skip: {_aim_route_err}")


    # Dispatcher DRY-RUN (no behavior change)
    try:
        if _dispatcher:
            _model_hint = (arguments or {}).get("model", "auto")
            logger.debug(f"[DISPATCHER-DRYRUN] req_id={req_id} tool={name} model_hint={_model_hint}")
            # Attempt non-operative route call; ignore any result
            try:
                _ = _dispatcher.route(name, arguments or {})
            except Exception as _route_err:
                logger.debug(f"[DISPATCHER-DRYRUN] route noop failed: {_route_err}")
    except Exception as _dry_err:
        logger.debug(f"[DISPATCHER-DRYRUN] skip: {_dry_err}")

    """
    Handle incoming tool execution requests from MCP clients.

    This is the main request dispatcher that routes tool calls to their appropriate handlers.
    It supports both AI-powered tools (from TOOLS registry) and utility tools (implemented as
    static functions).

    CONVERSATION LIFECYCLE MANAGEMENT:
    This function serves as the central orchestrator for multi-turn AI-to-AI conversations:

    1. THREAD RESUMPTION: When continuation_id is present, it reconstructs complete conversation
       context from in-memory storage including conversation history and file references

    2. CROSS-TOOL CONTINUATION: Enables seamless handoffs between different tools (analyze â†’
       codereview â†’ debug) while preserving full conversation context and file references

    3. CONTEXT INJECTION: Reconstructed conversation history is embedded into tool prompts
       using the dual prioritization strategy:
       - Files: Newest-first prioritization (recent file versions take precedence)
       - Turns: Newest-first collection for token efficiency, chronological presentation for LLM

    4. FOLLOW-UP GENERATION: After tool execution, generates continuation offers for ongoing
       AI-to-AI collaboration with natural language instructions

    STATELESS TO STATEFUL BRIDGE:
    The MCP protocol is inherently stateless, but this function bridges the gap by:
    - Loading persistent conversation state from in-memory storage
    - Reconstructing full multi-turn context for tool execution
    - Enabling tools to access previous exchanges and file references
    - Supporting conversation chains across different tool types

    Args:
        name: The name of the tool to execute (e.g., "analyze", "chat", "codereview")
        arguments: Dictionary of arguments to pass to the tool, potentially including:
                  - continuation_id: UUID for conversation thread resumption
                  - files: File paths for analysis (subject to deduplication)
                  - prompt: User request or follow-up question
                  - model: Specific AI model to use (optional)

    Returns:
        List of TextContent objects containing:
        - Tool's primary response with analysis/results
        - Continuation offers for follow-up conversations (when applicable)
        - Structured JSON responses with status and content

    Raises:
        ValueError: If continuation_id is invalid or conversation thread not found
        Exception: For tool-specific errors or execution failures

    Example Conversation Flow:
        1. Claude calls analyze tool with files â†’ creates new thread
        2. Thread ID returned in continuation offer
        3. Claude continues with codereview tool + continuation_id â†’ full context preserved
        4. Multiple tools can collaborate using same thread ID
    """
    logger.info(f"MCP tool call: {name} req_id={req_id}")
    logger.debug(f"MCP tool arguments: {list(arguments.keys())} req_id={req_id}")

    # Thinking tool aliasing/rerouting (name-level) before registry lookup
    try:
        if THINK_ROUTING_ENABLED:
            original_name = name
            lower_name = (name or "").lower()
            # Reroute rules:
            # 1) exact 'deepthink' -> 'thinkdeep'
            # 2) unknown tool name containing 'think' (case-insensitive) -> 'thinkdeep'
            # 3) do NOT reroute if a valid tool other than thinkdeep contains 'think'

            # Determine current active tool names
            active_tool_names = set(TOOLS.keys())

            reroute = False
            if lower_name == "deepthink":
                reroute = True
            elif lower_name not in active_tool_names and "think" in lower_name:
                reroute = True

            if reroute:
                # Respect rule (3): if name is a valid tool (not thinkdeep), don't reroute
                if lower_name in active_tool_names and lower_name != "thinkdeep":
                    pass  # no-op
                else:
                    name = "thinkdeep"
                    logger.info(f"REROUTE: '{original_name}' â†’ 'thinkdeep'")
    except Exception as _e:
        logger.debug(f"[THINK_ROUTING] aliasing skipped/failed: {_e}")

    # Log to activity file for monitoring
    try:
        mcp_activity_logger = logging.getLogger("mcp_activity")
        # Dynamically re-enable if env now permits (ensure TOOL_CALL visibility)
        if getattr(mcp_activity_logger, "disabled", False) and _env_true("ACTIVITY_LOG", "true"):
            mcp_activity_logger.disabled = False
        mcp_activity_logger.info(f"TOOL_CALL: {name} with {len(arguments)} arguments req_id={req_id}")
    except Exception:
        pass
    # Initialize JSONL event (boundary start) and monitoring helpers
    try:
        from utils.tool_events import ToolCallEvent as __Evt, ToolEventSink as __Sink
        _ex_mirror = _env_true("EX_MIRROR_ACTIVITY_TO_JSONL", "false")
        _evt = __Evt(provider="boundary", tool_name=name, args={"arg_count": len(arguments), "req_id": req_id})
        _sink = __Sink()
    except Exception:
        _ex_mirror = False
        _evt = None
        _sink = None

    # Watchdog and timeout configuration
    import asyncio as _asyncio
    import time as _time
    try:
        _tool_timeout_s = float(os.getenv("EX_TOOL_TIMEOUT_SECONDS", "120"))
        _hb_every_s = float(os.getenv("EX_HEARTBEAT_SECONDS", "10"))
        _warn_after_s = float(os.getenv("EX_WATCHDOG_WARN_SECONDS", "30"))
        _err_after_s = float(os.getenv("EX_WATCHDOG_ERROR_SECONDS", "90"))
    except Exception:
        _tool_timeout_s, _hb_every_s, _warn_after_s, _err_after_s = 120.0, 10.0, 30.0, 90.0

    async def _execute_with_monitor(_coro_factory):
        start = _time.time()
        # background heartbeat
        mcp_logger = logging.getLogger("mcp_activity")
        _stop = False
        async def _heartbeat():
            last_warned = False
            while not _stop:
                elapsed = _time.time() - start
                try:
                    if elapsed >= _err_after_s:
                        mcp_logger.error(f"[WATCHDOG] tool={name} req_id={req_id} elapsed={elapsed:.1f}s — escalating")
                    elif elapsed >= _warn_after_s and not last_warned:
                        mcp_logger.warning(f"[WATCHDOG] tool={name} req_id={req_id} elapsed={elapsed:.1f}s — still running")
                        last_warned = True
                    else:
                        mcp_logger.info(f"[PROGRESS] tool={name} req_id={req_id} elapsed={elapsed:.1f}s — heartbeat")
                except Exception:
                    pass
                try:
                    await _asyncio.sleep(_hb_every_s)
                except Exception:
                    break

        hb_task = _asyncio.create_task(_heartbeat())
        _t0 = __import__('time').time()
        try:
            main_task = _asyncio.create_task(_coro_factory())
            result = await _asyncio.wait_for(main_task, timeout=_tool_timeout_s)
            # record success
            try:
                if _ex_mirror and _evt and _sink:
                    _evt.end(ok=True)
                    _sink.record(_evt)
            except Exception:
                pass
            return result
        except _asyncio.CancelledError:
            # Propagate cancellation (e.g., client disconnect) but record structured end
            try:
                _dt = max(0.0, __import__('time').time() - (_t0 if '_t0' in locals() else __import__('time').time()))
                _thr = float((__import__('os').getenv('EX_CLIENT_ABORT_THRESHOLD_SECS') or '10').strip())
                _evt_payload = {
                    "event": "client_abort_suspected" if _dt < _thr else "tool_cancelled",
                    "tool": name,
                    "req_id": req_id,
                    "elapsed_sec": round(_dt, 3),
                    "threshold_sec": _thr,
                }
                logging.getLogger("mcp_activity").info(_evt_payload)
                mcp_logger.info(f"TOOL_CANCELLED: {name} req_id={req_id} elapsed={_dt:.2f}s thr={_thr:.1f}s")
            except Exception:
                pass
            try:
                main_task.cancel()
            except Exception:
                pass
            try:
                if _ex_mirror and _evt and _sink:
                    _evt.end(ok=False, error="cancelled")
                    _sink.record(_evt)
            except Exception:
                pass
            raise


        finally:
            _stop = True
            try:
                hb_task.cancel()
            except Exception:
                pass

    # Handle thread context reconstruction if continuation_id is present
    if "continuation_id" in arguments and arguments["continuation_id"]:
        continuation_id = arguments["continuation_id"]
        logger.debug(f"Resuming conversation thread: {continuation_id}")
        logger.debug(
            f"[CONVERSATION_DEBUG] Tool '{name}' resuming thread {continuation_id} with {len(arguments)} arguments"
        )
        logger.debug(f"[CONVERSATION_DEBUG] Original arguments keys: {list(arguments.keys())}")

        # Log to activity file for monitoring
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"CONVERSATION_RESUME: {name} resuming thread {continuation_id} req_id={req_id}")
        except Exception:
            pass

        arguments = await reconstruct_thread_context(arguments)
        logger.debug(f"[CONVERSATION_DEBUG] After thread reconstruction, arguments keys: {list(arguments.keys())}")
        if "_remaining_tokens" in arguments:
            logger.debug(f"[CONVERSATION_DEBUG] Remaining token budget: {arguments['_remaining_tokens']:,}")
    # Session cache (memory-only) integration (env-gated via presence of CACHE_* envs)
    try:
        from utils.cache import get_session_cache, make_session_key
        cache = get_session_cache()
        cont_id = arguments.get("continuation_id")
        if cont_id:
            skey = make_session_key(cont_id)
            cached = cache.get(skey)
            if cached:
                logger.debug(f"[CACHE] hit for {skey}; injecting compact context")
                # Inject compact context hints for tools
                arguments.setdefault("_cached_summary", cached.get("summary"))
                arguments.setdefault("_cached_files", cached.get("files", []))
            else:
                logger.debug(f"[CACHE] miss for {skey}")
    except Exception as _e:
        logger.debug(f"[CACHE] integration skipped/failed: {_e}")
        # Consensus: auto-select models when not provided (default-safe)
        try:
            if name == "consensus":
                models_arg = arguments.get("models")
                if not models_arg and os.getenv("ENABLE_CONSENSUS_AUTOMODE", "true").strip().lower() == "true":
                    from src.providers.registry import ModelProviderRegistry
                    from src.providers.base import ProviderType

                    def _int_env(k: str, d: int) -> int:
                        try:
                            return int(os.getenv(k, str(d)))
                        except Exception:
                            return d

                    min_needed = _int_env("MIN_CONSENSUS_MODELS", 2)
                    max_needed = max(_int_env("MAX_CONSENSUS_MODELS", 3), min_needed)

                    available_map = ModelProviderRegistry.get_available_models(respect_restrictions=True)
                    available = set(available_map.keys())

                    # Preferred quality-tier from env
                    prefs = [
                        os.getenv("GLM_QUALITY_MODEL"),
                        os.getenv("KIMI_QUALITY_MODEL"),
                    ]
                    # Speed-tier complements
                    speed_prefs = [
                        os.getenv("GLM_SPEED_MODEL"),
                        os.getenv("KIMI_SPEED_MODEL"),
                    ]

                    chosen: list[str] = []
                    for m in prefs:
                        if m and m in available and m not in chosen:
                            chosen.append(m)
                            if len(chosen) >= max_needed:
                                break

                    if len(chosen) < min_needed:
                        for m in speed_prefs:
                            if m and m in available and m not in chosen:
                                chosen.append(m)
                                if len(chosen) >= max_needed:
                                    break

                    # Fill remaining from provider priority order
                    if len(chosen) < min_needed:
                        for ptype in ModelProviderRegistry.PROVIDER_PRIORITY_ORDER:
                            try:
                                pool = ModelProviderRegistry.list_available_models(provider_type=ptype)
                            except Exception:
                                pool = []
                            for m in pool:
                                if m in available and m not in chosen:
                                    chosen.append(m)
                                    if len(chosen) >= max_needed:
                                        break
                            if len(chosen) >= max_needed:
                                break

                    if not chosen:
                        warn_text = (
                            "Consensus requires at least one available model; none were found under current providers. "
                            "Configure provider keys or set DEFAULT_MODEL=auto."
                        )
                        logger.warning("[CONSENSUS] %s", warn_text)
                        return [TextContent(type="text", text=warn_text)]

                    if len(chosen) == 1:
                        logger.warning("[CONSENSUS] Only 1 model available; proceeding without cross-model comparison")

                    logger.info("Consensus invoked with %d model(s)", len(chosen))
                    logger.debug("[CONSENSUS] Auto-selected models: %s", ", ".join(chosen))

                    arguments["models"] = [{"model": m} for m in chosen[:max_needed]]
        except Exception as _e:
            logger.debug(f"[CONSENSUS] auto-select models skipped/failed: {_e}")



    # Route to AI-powered tools that require Gemini API calls
    if name in TOOLS:
        logger.info(f"Executing tool '{name}' with {len(arguments)} parameter(s)")
        tool = TOOLS[name]
        # Optional: hot-reload env on every call so EX_ACTIVITY_* toggles are live
        try:
            if _env_true("EX_HOTRELOAD_ENV", "false"):
                _hot_reload_env()
        except Exception:
            pass
        # Begin per-call progress capture buffer (in addition to logs)
        try:
            start_progress_capture()
        except Exception:
            pass

        # EARLY MODEL RESOLUTION AT MCP BOUNDARY
        # Resolve model before passing to tool - this ensures consistent model handling
        # NOTE: Consensus tool is exempt as it handles multiple models internally
        # Centralized model:auto routing policy (simple vs deep)
        def _route_auto_model(tool_name: str, requested: str | None, args: dict[str, Any]) -> str | None:
            try:
                req = (requested or "").strip().lower()
                if req and req != "auto":
                    return requested  # explicit model respected
                # Route Kimi-specific tools to Kimi by default
                kimi_tools = {"kimi_chat_with_tools", "kimi_upload_and_extract"}
                if tool_name in kimi_tools:
                    return os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")

                simple_tools = {"chat","status","provider_capabilities","listmodels","activity","version"}
                if tool_name in simple_tools:
                    return os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")

                # Step-aware heuristics for workflows (Option B)
                step_number = args.get("step_number")
                next_step_required = args.get("next_step_required")
                depth = str(args.get("depth") or "").strip().lower()

                # thinkdeep: always deep
                if tool_name == "thinkdeep":
                    return os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")

                # analyze
                if tool_name == "analyze":
                    if (step_number == 1 and (next_step_required is True)):
                        return os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
                    # final step or unknown -> deep by default
                    return os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")

                # codereview/refactor/debug/testgen/planner
                if tool_name in {"codereview","refactor","debug","testgen","planner"}:
                    if depth == "deep" or (next_step_required is False):
                        return os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")
                    if step_number == 1:
                        return os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
                    # Default lean toward flash unless final/deep
                    return os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")

                # consensus/docgen/secaudit: deep
                if tool_name in {"consensus","docgen","secaudit"}:
                    return os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")

                # Default: prefer GLM flash
                return os.getenv("DEFAULT_AUTO_MODEL", "glm-4.5-flash")
            except Exception:
                return requested

        from src.providers.registry import ModelProviderRegistry
        from utils.file_utils import check_total_file_size
        from utils.model_context import ModelContext

        # Get model from arguments or use default, then apply centralized auto routing
        requested_model = arguments.get("model") or DEFAULT_MODEL
        routed_model = _route_auto_model(name, requested_model, arguments)
        model_name = routed_model or requested_model
        # Propagate routed model to arguments so downstream logic treats it as explicit
        try:
            arguments["model"] = model_name
        except Exception:
            pass
        # Single-line boundary log for routing/fallback reasons
        try:
            reason = "explicit" if (requested_model and str(requested_model).lower() != "auto") else (
                "auto_step1" if (name=="analyze" and arguments.get("step_number")==1 and arguments.get("next_step_required") is True) else (
                "auto_deep" if name in {"thinkdeep","consensus","docgen","secaudit"} or arguments.get("depth")=="deep" or arguments.get("next_step_required") is False else "auto_simple"
            ))
            logger.info(f"[MODEL_ROUTE] tool={name} requested={requested_model} resolved={model_name} reason={reason}")
            try:
                logging.getLogger("mcp_activity").info({
                    "event": "route_diagnostics",
                    "tool": name,
                    "req_id": req_id,
                    "requested_model": requested_model,
                    "resolved_model": model_name,
                    "reason": reason,
                    "path": "model_resolution"
                })
            except Exception:
                pass
        except Exception:
            pass

        # Parse model:option format if present
        model_name, model_option = parse_model_option(model_name)
        if model_option:
            logger.info(f"Parsed model format - model: '{model_name}', option: '{model_option}'")
        else:
            logger.info(f"Parsed model format - model: '{model_name}'")
        # Early boundary routing attempt log for observability
        try:
            hidden_enabled_early = _env_true("HIDDEN_MODEL_ROUTER_ENABLED", "false")
            sentinels_early = {s.strip().lower() for s in os.getenv("ROUTER_SENTINEL_MODELS", "auto").split(",") if s.strip()}
            logging.getLogger("server").info(
                f"EVENT boundary_model_resolution_attempt input_model={model_name} "
                f"tool={getattr(tool, '__class__', type(tool)).__name__} "
                f"sentinel_match={str(model_name).strip().lower() in sentinels_early} "
                f"hidden_router={hidden_enabled_early}"
            )
        except Exception as e:
            logging.getLogger("server").warning("boundary_model_resolution_attempt log failed", exc_info=True)


        # Deterministic thinking model selection for thinkdeep
        try:
            if THINK_ROUTING_ENABLED and name == "thinkdeep":
                explicit_model = "model" in arguments and str(arguments.get("model") or "").strip().lower() not in {"", "auto"}
                override_explicit = _os.getenv("THINKDEEP_OVERRIDE_EXPLICIT", "true").strip().lower() == "true"
                want_expert = bool(arguments.get("use_assistant_model", False))
                if (not explicit_model) or (override_explicit and want_expert):
                    # Choose fast expert model for thinkdeep to avoid long waits/timeouts (or Kimi thinking if disabled)
                    requested_input = arguments.get("model")
                    fast = (_os.getenv("THINKDEEP_FAST_EXPERT", "true").strip().lower() == "true")
                    if fast:
                        model_name = _os.getenv("GLM_FLASH_MODEL", "glm-4.5-flash")
                        reason = "forced_glm_flash_fast"
                    else:
                        model_name = _os.getenv("KIMI_THINKING_MODEL", "kimi-thinking-preview")
                        reason = "forced_kimi_thinking"
                    arguments["model"] = model_name
                    logger.info(f"THINKING MODEL (router): requested='{requested_input}' chosen='{model_name}' reason='{reason}'")
        except Exception as _e:
            logger.debug(f"[THINKING] model selection skipped/failed: {_e}")

        # Consensus tool handles its own model configuration validation
        # No special handling needed at server level

        # Skip model resolution for tools that don't require models (e.g., planner)
        if not tool.requires_model():
            logger.debug(f"Tool {name} doesn't require model resolution - skipping model validation")
            # Execute tool directly without model context
            try:
                if name in {"kimi_multi_file_chat", "kimi_chat_with_tools"}:
                    # All file_chat requests must pass through fallback orchestrator
                    try:
                        logging.getLogger("mcp_activity").info({
                            "event": "route_diagnostics",
                            "tool": name,
                            "req_id": req_id,
                            "path": "non_model_dispatch",
                            "note": "manager dispatcher engaged; invoking safety-net orchestrator"
                        })
                    except Exception:
                        pass
                    try:
                        logging.getLogger("mcp_activity").info("[FALLBACK] orchestrator route engaged for multi-file chat")
                    except Exception:
                        pass
                    try:
                        if name == "kimi_multi_file_chat":
                            from src.server.fallback_orchestrator import execute_file_chat_with_fallback as _fb
                        else:
                            from src.server.fallback_orchestrator import execute_chat_with_tools_with_fallback as _fb
                    except Exception:
                        # Orchestrator unavailable; execute primary tool directly
                        return await _execute_with_monitor(lambda: tool.execute(arguments))
                    return await _fb(TOOLS, _execute_with_monitor, name, arguments)
                else:
                    return await _execute_with_monitor(lambda: tool.execute(arguments))
            except Exception as e:
                # Graceful error normalization for invalid arguments and runtime errors
                try:
                    from pydantic import ValidationError as _ValidationError
                except Exception:
                    _ValidationError = None  # type: ignore
                from mcp.types import TextContent as _TextContent
                import json as _json
                if _ValidationError and isinstance(e, _ValidationError):
                    err = {
                        "status": "invalid_request",
                        "error": "Invalid arguments for tool",
                        "details": str(e),
                        "tool": name,
                    }
                    logger.warning("Tool %s argument validation failed: %s", name, e)
                    return [_TextContent(type="text", text=_json.dumps(err))]
                logger.error("Tool %s execution failed: %s", name, e, exc_info=True)
                err = {
                    "status": "execution_error",
                    "error": str(e),
                    "tool": name,
                }
                return [_TextContent(type="text", text=_json.dumps(err))]

        # Auto model selection helper
        def _has_cjk(text: str) -> bool:
            try:
                if not text:
                    return False
                # Quick CJK block detection
                return any(("\u4e00" <= ch <= "\u9fff") or ("\u3040" <= ch <= "\u30ff") or ("\u3400" <= ch <= "\u4dbf") for ch in text)
            except Exception:
                return False

        # Backward-compatible inner wrapper. Prefer module-level _resolve_auto_model.
        def resolve_auto_model(args: dict[str, Any], tool_obj) -> str:  # noqa: F811
            # Inspect providers
            available = ModelProviderRegistry.get_available_models(respect_restrictions=True)
            from src.providers.base import ProviderType
            has_glm = any(pt == ProviderType.GLM for pt in available.values())
            has_kimi = any(pt == ProviderType.KIMI for pt in available.values())
            has_custom = any(pt == ProviderType.CUSTOM for pt in available.values())

            locale = _os.getenv("LOCALE", "").lower()
            prompt = args.get("prompt", "") or args.get("_original_user_prompt", "") or ""
            local_only = bool(args.get("local_only"))
            chosen = None
            reason = None


            # Intelligent selection by tool category (env-gated)
            try:
                if os.getenv("ENABLE_INTELLIGENT_SELECTION", "true").strip().lower() == "true":
                    cat_obj = tool_obj.get_model_category() if hasattr(tool_obj, "get_model_category") else None
                    cat_name = getattr(cat_obj, "name", None)
                    if cat_name:
                        # Choose quality-tier for extended reasoning; speed-tier for fast/balanced
                        if cat_name == "EXTENDED_REASONING":
                            if (locale.startswith("zh") or _has_cjk(prompt)) and has_kimi:
                                chosen = os.getenv("KIMI_QUALITY_MODEL", os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview"))
                                reason = "intelligent_ext_reasoning_kimi"
                            elif has_glm:
                                chosen = os.getenv("GLM_QUALITY_MODEL", "glm-4.5")
                                reason = "intelligent_ext_reasoning_glm"
                        elif cat_name in ("BALANCED", "FAST_RESPONSE"):
                            if has_glm:
                                chosen = os.getenv("GLM_SPEED_MODEL", "glm-4.5-flash")
                                reason = "intelligent_speed_glm"
                            elif has_kimi:
                                chosen = os.getenv("KIMI_SPEED_MODEL", "kimi-k2-turbo-preview")
                                reason = "intelligent_speed_kimi"
                    # If still not chosen, fall through to legacy logic below
            except Exception:
                pass

            # 1) Locale or content indicates CJK â†’ prefer Kimi
            if (locale.startswith("zh") or _has_cjk(prompt)) and has_kimi:
                chosen = os.getenv("KIMI_DEFAULT_MODEL", "kimi-k2-0711-preview")
                reason = "cjk_locale_or_content"
            # 2) Local-only tasks â†’ prefer Custom
            elif local_only and has_custom:
                chosen = os.getenv("CUSTOM_MODEL_NAME", "llama3.2")
                reason = "local_only"
            # 3) Default GLM fast model if present
            elif has_glm:
                chosen = "glm-4.5-flash"
                reason = "default_glm"
            # 4) Provider-registry fallback by tool category
            else:
                cat = tool_obj.get_model_category() if hasattr(tool_obj, "get_model_category") else None
                chosen = ModelProviderRegistry.get_preferred_fallback_model(cat)
                reason = "provider_fallback"

            # Log structured selection
            try:
                sel_log = {
                    "event": "auto_model_selected",
                    "tool": getattr(tool_obj, "__class__", type(tool_obj)).__name__,
                    "model": chosen,
                    "reason": reason,
                    "locale": locale,
                    "has_glm": has_glm,
                    "has_kimi": has_kimi,
                    "has_custom": has_custom,
                    "local_only": local_only,
                }
                logging.getLogger().info(sel_log)
            except Exception:
                pass
            return chosen


        # Handle auto or hidden-sentinel at MCP boundary - resolve to specific model (production selector)
        hidden_enabled = _env_true("HIDDEN_MODEL_ROUTER_ENABLED", "false")
        sentinels = {s.strip().lower() for s in os.getenv("ROUTER_SENTINEL_MODELS", "auto").split(",") if s.strip()}
        # Always log boundary attempt for observability
        try:
            logging.getLogger('server').info({
                "event": "boundary_model_resolution_attempt",
                "req_id": req_id,
                "input_model": model_name,
                "tool": getattr(tool, "__class__", type(tool)).__name__,
                "sentinel_match": model_name.strip().lower() in sentinels,
                "hidden_router": hidden_enabled,
            })
        except Exception:
            pass
        if model_name.lower() == "auto" or (hidden_enabled and model_name.strip().lower() in sentinels):

            # Use module-level function if available (test mocking)
            resolver = _resolve_auto_model or resolve_auto_model
            selected = resolver(arguments, tool)
            if selected:
                # Structured log for MCP-boundary selection
                try:
                    logger_server = logging.getLogger('server')
                    # Structured dict log
                    logger_server.info({
                        "event": "boundary_model_resolved",
                        "req_id": req_id,
                        "input_model": model_name,
                        "resolved_model": selected,
                        "tool": getattr(tool, "__class__", type(tool)).__name__,
                        "sentinel_match": model_name.strip().lower() in sentinels,
                        "hidden_router": hidden_enabled,
                    })
                    # Flat string log for simple grepping and EX-AI parsing
                    logger_server.info(
                        f"EVENT boundary_model_resolved input_model={model_name} resolved_model={selected} "
                        f"tool={getattr(tool, '__class__', type(tool)).__name__} req_id={req_id}"
                    )
                except Exception:
                    pass
                model_name = selected
                arguments["model"] = model_name

        # Validate model availability at MCP boundary (graceful fallback)
        provider = ModelProviderRegistry.get_provider_for_model(model_name)
        if not provider:
            # Try to recover gracefully before failing
            available_models = list(ModelProviderRegistry.get_available_models(respect_restrictions=True).keys())
            if not available_models:
                # Providers may not be initialized in this process yet; try again
                try:
                    configure_providers()
                    available_models = list(ModelProviderRegistry.get_available_models(respect_restrictions=True).keys())
                    provider = ModelProviderRegistry.get_provider_for_model(model_name)
                except Exception as _e:
                    logger.debug(f"configure_providers() retry failed: {_e}")
            if not provider:
                tool_category = tool.get_model_category()
                suggested_model = ModelProviderRegistry.get_preferred_fallback_model(tool_category)
                # If we have a suggested model, auto-fallback instead of erroring
                if suggested_model and suggested_model != model_name:
                    logger.info(f"[BOUNDARY] Auto-fallback: '{model_name}' -> '{suggested_model}' for tool {name}")
                    model_name = suggested_model
                    arguments["model"] = model_name
                else:
                    error_message = (
                        f"Model '{model_name}' is not available with current API keys. "
                        f"Available models: {', '.join(available_models)}. "
                        f"Suggested model for {name}: '{suggested_model}' "
                        f"(category: {tool_category.value})"
                    )
                    from mcp.types import TextContent as _TextContent
                    from tools.models import ToolOutput as _ToolOutput
                    error_output = _ToolOutput(
                        status="error",
                        content=error_message,
                        content_type="text",
                        metadata={"tool_name": name, "requested_model": model_name},
                    )
                    return [_TextContent(type="text", text=error_output.model_dump_json())]

        # Create model context with resolved model and option
        model_context = ModelContext(model_name, model_option)
        arguments["_model_context"] = model_context
        arguments["_resolved_model_name"] = model_name
        logger.debug(
            f"Model context created for {model_name} with {model_context.capabilities.context_window} token capacity"
        )
        if model_option:
            logger.debug(f"Model option stored in context: '{model_option}'")


        # Response content validator and diagnostics (insertion point around ~1600)
        def _validate_response_content(result_obj: object, _tool_name: str, _req_id: str):
            import json as _json
            _alog = logging.getLogger("mcp_activity")
            try:
                # Shape introspection
                if isinstance(result_obj, list):
                    n = len(result_obj)
                    _alog.info(f"RESPONSE_DEBUG: pre-normalize type=list len={n} tool={_tool_name} req_id={_req_id}")
                    if n == 0:
                        _alog.warning(f"RESPONSE_DEBUG: empty result list tool={_tool_name} req_id={_req_id}")
                    # Preview first few items
                    previews: list[str] = []
                    for idx, item in enumerate(result_obj[:3]):
                        try:
                            txt = getattr(item, "text", None)
                            if isinstance(txt, str):
                                previews.append(f"#{idx} {txt[:200].replace('\n',' ') }")
                                # If JSON envelope, check status/content
                                try:
                                    obj = _json.loads(txt)
                                    if isinstance(obj, dict):
                                        st = str(obj.get("status", "")).lower().strip()
                                        if st in {"success", "ok", "completed"} and not obj.get("content"):
                                            _alog.warning(f"RESPONSE_DEBUG: success with empty content idx={idx} tool={_tool_name} req_id={_req_id}")
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    if previews:
                        try:
                            _alog.info(f"RESPONSE_DEBUG: previews: {' | '.join(previews)} tool={_tool_name} req_id={_req_id}")
                        except Exception:
                            pass
                else:
                    _alog.info(f"RESPONSE_DEBUG: pre-normalize type={type(result_obj).__name__} tool={_tool_name} req_id={_req_id}")
                    try:
                        txt = getattr(result_obj, "text", None)
                        if isinstance(txt, str) and not txt.strip():
                            _alog.warning(f"RESPONSE_DEBUG: single TextContent empty text tool={_tool_name} req_id={_req_id}")
                    except Exception:
                        pass
            except Exception as _ve:
                try:
                    _alog.debug(f"RESPONSE_DEBUG: validator error: {_ve}")
                except Exception:
                    pass
            return result_obj

        # EARLY FILE SIZE VALIDATION AT MCP BOUNDARY
        # Check file sizes before tool execution using resolved model
        if "files" in arguments and arguments["files"]:
            logger.debug(f"Checking file sizes for {len(arguments['files'])} files with model {model_name}")
            if _env_true("STRICT_FILE_SIZE_REJECTION", "false"):
                file_size_check = check_total_file_size(arguments["files"], model_name)
                if file_size_check:
                    logger.warning(f"File size check failed for {name} with model {model_name}")
                    return [TextContent(type="text", text=ToolOutput(**file_size_check).model_dump_json())]

        # Optional date injection for temporal awareness
        try:
            import datetime as _dt
            if _env_true("INJECT_CURRENT_DATE", "true"):
                fmt = _os.getenv("DATE_FORMAT", "%Y-%m-%d")
                today = _dt.datetime.now().strftime(fmt)
                # Store in arguments for tools that wish to render it in prompts
                arguments["_today"] = today
        except Exception:
            pass

        # Smart websearch (thinkdeep) - conservative, default off
        try:
            if name == "thinkdeep":
                if "use_websearch" not in arguments:
                    if _env_true("ENABLE_SMART_WEBSEARCH", "false"):
                        import re
                        prompt_text = (arguments.get("prompt") or arguments.get("_original_user_prompt") or "")
                        lowered = prompt_text.lower()
                        recent_date = re.search(r"\b20\d{2}-\d{2}-\d{2}\b", lowered)  # YYYY-MM-DD

                        triggers = [
                            "today", "now", "this week", "as of", "release notes", "changelog",
                        ]
                        if (
                            any(t in lowered for t in triggers)
                            or recent_date
                            or re.search(r"cve-\d{4}-\d+", lowered)
                        ):
                            arguments["use_websearch"] = True
                            logger.debug("[SMART_WEBSEARCH] enabled for thinkdeep due to time-sensitive cues")
        except Exception:
            pass

        # Client-aware defaults (generic profile with legacy Claude fallback)
        try:
            from utils.client_info import get_client_info_from_context
            ci = get_client_info_from_context(server) or {}
            # Generic env first, then legacy Claude-specific variables
            if _env_true("CLIENT_DEFAULTS_USE_WEBSEARCH", os.getenv("CLAUDE_DEFAULTS_USE_WEBSEARCH","false")):
                if "use_websearch" not in arguments:
                    arguments["use_websearch"] = True
            if name == "thinkdeep" and "thinking_mode" not in arguments:
                default_thinking = (os.getenv("CLIENT_DEFAULT_THINKING_MODE") or os.getenv("CLAUDE_DEFAULT_THINKING_MODE","medium")).strip().lower()
                arguments["thinking_mode"] = default_thinking
        except Exception:
            pass

        # Execute tool with pre-resolved model context
        __overall_start = _time.time()
        __workflow_steps_completed = 1
        if name in {"kimi_multi_file_chat", "kimi_chat_with_tools"}:
            # All file_chat requests must pass through fallback orchestrator
            try:
                logging.getLogger("mcp_activity").info({
                    "event": "route_diagnostics",
                    "tool": name,

                    "req_id": req_id,
                    "path": "non_model_dispatch",
                    "note": "manager dispatcher engaged; invoking safety-net orchestrator"
                })
            except Exception:
                pass
            try:
                logging.getLogger("mcp_activity").info("[FALLBACK] orchestrator route engaged for multi-file chat")
            except Exception:
                pass
            try:
                if name == "kimi_multi_file_chat":
                    from src.server.fallback_orchestrator import execute_file_chat_with_fallback as _fb
                else:
                    from src.server.fallback_orchestrator import execute_chat_with_tools_with_fallback as _fb
                result = await _fb(TOOLS, _execute_with_monitor, name, arguments)
            except Exception:
                result = await _execute_with_monitor(lambda: tool.execute(arguments))
        else:
            result = await _execute_with_monitor(lambda: tool.execute(arguments))
        # Normalize result shape to list[TextContent]
        from mcp.types import TextContent as _TextContent
        # Enhanced logging and validation prior to normalization
        try:
            _alog = logging.getLogger("mcp_activity")
            _alog.info(f"RESPONSE_DEBUG: raw_result_type={type(result).__name__} is_list={isinstance(result, list)} tool={name} req_id={req_id}")
            if isinstance(result, list):
                _alog.info(f"RESPONSE_DEBUG: raw_result_len={len(result)} tool={name} req_id={req_id}")
                prevs = []
                for _i, _it in enumerate(result[:3]):
                    try:
                        _t = getattr(_it, "text", None)
                        if isinstance(_t, str):
                            prevs.append(f"#{_i} {_t[:160].replace('\n',' ')}")
                    except Exception:
                        pass
                if prevs:
                    _alog.info(f"RESPONSE_DEBUG: raw_previews: {' | '.join(prevs)} tool={name} req_id={req_id}")
        except Exception:
            pass
        # Validate content before normalization to catch empty/invalid shapes early
        result = _validate_response_content(result, name, req_id)

        if isinstance(result, _TextContent):
            result = [result]
        elif not isinstance(result, list):
            # best-effort fallback
            try:
                result = [_TextContent(type="text", text=str(result))]
            except Exception:
                result = []
        try:
            _nlen = len(result) if isinstance(result, list) else 0
            logging.getLogger("mcp_activity").info(f"RESPONSE_DEBUG: normalized_result_len={_nlen} tool={name} req_id={req_id}")
        except Exception:
            pass


        # Optional auto-continue for workflow tools (env-gated)
        try:
            import json as _json
            from mcp.types import TextContent as _TextContent
            auto_en = _env_true("EX_AUTOCONTINUE_WORKFLOWS", "false")
            only_think = _env_true("EX_AUTOCONTINUE_ONLY_THINKDEEP", "true")
            max_steps = int(os.getenv("EX_AUTOCONTINUE_MAX_STEPS", "3"))
            # Apply optional per-client workflow step cap (generic with legacy fallback)
            try:
                cap = int((os.getenv("CLIENT_MAX_WORKFLOW_STEPS") or os.getenv("CLAUDE_MAX_WORKFLOW_STEPS","0") or "0"))
                if cap > 0:
                    max_steps = min(max_steps, cap)
            except Exception:
                pass

            steps = 0
            if auto_en and isinstance(result, list) and result:
                while steps < max_steps:
                    primary = result[-1]
                    text = None
                    if isinstance(primary, _TextContent) and primary.type == "text":
                        text = primary.text or ""
                    elif isinstance(primary, dict):
                        text = primary.get("text")
                    if not text:
                        break
                    try:
                        data = _json.loads(text)
                    except Exception:
                        break
                    status = str(data.get("status", ""))
                    if not status.startswith("pause_for_"):
                        break
                    if only_think and name != "thinkdeep":
                        break
                    next_call = data.get("next_call") or {}
                    next_args = dict(next_call.get("arguments") or {})
                    if not next_args:
                        break
                    # Ensure continuation and model are present
                    if not next_args.get("continuation_id"):
                        cid = data.get("continuation_id") or arguments.get("continuation_id")
                        if cid:
                            next_args["continuation_id"] = cid
                    if not next_args.get("model"):
                        next_args["model"] = arguments.get("model") or model_name
                    # Execute next step directly
                    logger.info(f"[AUTO-CONTINUE] Executing next step for {name}: step_number={next_args.get('step_number')}")
                    result = await _execute_with_monitor(lambda: tool.execute(next_args))
                    # Normalize result shape for auto-continued step
                    from mcp.types import TextContent as _TextContent
                    if isinstance(result, _TextContent):
                        result = [result]
                    elif not isinstance(result, list):
                        try:
                            result = [_TextContent(type="text", text=str(result))]
                        except Exception:
                            result = []
                    steps += 1
                try:
                    __workflow_steps_completed = 1 + int(steps)
                except Exception:
                    __workflow_steps_completed = 1
        except Exception as _e:
            logger.debug(f"[AUTO-CONTINUE] skipped/failed: {_e}")

        logger.info(f"Tool '{name}' execution completed")

        # Attach captured progress (if any) to the last TextContent as JSON metadata
        try:
            progress_log = get_progress_log()
            if isinstance(result, list) and result:
                from mcp.types import TextContent as _TextContent
                primary = result[-1]
                progress_block = None
                if progress_log:
                    progress_block = "\n".join(["[PROGRESS] " + p for p in progress_log])
                    if isinstance(primary, _TextContent) and primary.type == "text":
                        import json as _json
                        text = primary.text or ""
                        try:
                            data = _json.loads(text)
                        except Exception:
                            data = None
                        if isinstance(data, dict):
                            data.setdefault("metadata", {})["progress"] = progress_log
                            try:
                                if isinstance(data.get("content"), str):
                                    data["content"] = f"=== PROGRESS ===\n{progress_block}\n=== END PROGRESS ===\n\n" + data["content"]
                                else:
                                    data["progress_text"] = progress_block
                            except Exception:
                                data["progress_text"] = progress_block
                            primary.text = _json.dumps(data, ensure_ascii=False)
                # Always include a visible activity summary block for UI dropdowns (unconditional)
                try:
                    from mcp.types import TextContent as _Txt
                    from utils.token_utils import estimate_tokens as __est_tokens
                    import json as _json
                    tail = f"=== PROGRESS ===\n{progress_block}\n=== END PROGRESS ===" if progress_block else "(no progress captured)"

                    # Build MCP CALL SUMMARY (final status, steps, duration, model, tokens, continuation, expert)
                    __total_dur = 0.0
                    try:
                        __total_dur = max(0.0, _time.time() - __overall_start)
                    except Exception:
                        __total_dur = 0.0
                    __last_text = None
                    try:
                        __primary = result[-1] if isinstance(result, list) and result else None
                        if isinstance(__primary, _Txt):
                            __last_text = __primary.text or ""
                        elif isinstance(__primary, dict):
                            __last_text = __primary.get("text")
                    except Exception:
                        __last_text = None
                    __meta = {}
                    try:
                        if __last_text:
                            __meta = _json.loads(__last_text)
                        else:
                            __meta = {}
                    except Exception:
                        __meta = {}
                    __next_req = bool(__meta.get("next_step_required") is True)
                    __status = str(__meta.get("status") or ("pause_for_analysis" if __next_req else "ok")).upper()
                    __step_no = __meta.get("step_number") or __workflow_steps_completed
                    __total_steps = __meta.get("total_steps")
                    __cid = __meta.get("continuation_id") or arguments.get("continuation_id")
                    __model_used = arguments.get("model") or model_name
                    try:
                        __tokens = 0
                        for __blk in (result or []):
                            if isinstance(__blk, _Txt):
                                __tokens += __est_tokens(__blk.text or "")
                            elif isinstance(__blk, dict):
                                __tokens += __est_tokens(str(__blk.get("text") or ""))
                    except Exception:
                        __tokens = 0
                    __expert_flag = bool(arguments.get("use_assistant_model") or __meta.get("use_assistant_model"))
                    if __expert_flag:
                        __expert_status = "Pending" if __next_req else "Completed"
                    else:
                        __expert_status = "Disabled"
                    __status_label = "WORKFLOW_PAUSED" if __next_req or (__status.startswith("PAUSE_FOR_")) else "COMPLETE"
                    __next_action = f"Continue with step {((__step_no or 0) + 1)}" if __next_req else "None"
                    __summary_text = (
                        "=== MCP CALL SUMMARY ===\n"
                        f"Tool: {name} | Status: {__status_label} (Step {__step_no}/{__total_steps or '?'} complete)\n"
                        f"Duration: {__total_dur:.1f}s | Model: {__model_used} | Tokens: ~{__tokens}\n"
                        f"Continuation ID: {__cid or '-'}\n"
                        f"Next Action Required: {__next_action}\n"
                        f"Expert Validation: {__expert_status}\n"
                        "=== END SUMMARY ==="
                    )
                    # Prepare combined render (summary + progress)
                    # Optional compact summary line at top (off by default to avoid replacing first block)
                    try:
                        if _env_true("EX_ACTIVITY_SUMMARY_AT_TOP", "false"):
                            prog_count = len(progress_log) if progress_log else 0
                            summary = _Txt(type="text", text=f"Activity: {prog_count} progress events (req_id={req_id})")
                            # Put before all blocks so even 'show-first-only' UIs surface it
                            result.insert(0, summary)
                    except Exception:
                        pass

                    # Optionally render as a Markdown details block for UIs without native dropdowns
                    md_details = _env_true("EX_ACTIVITY_MARKDOWN_DETAILS", "true")
                    if md_details:
                        # Robust rendering: always include a visible plain-text block first,
                        # then an optional collapsible details section for UIs that support it.
                        tail_render = (
                            f"{__summary_text}\n\n{tail}\nreq_id={req_id}\n\n"
                            f"<details><summary>Tool activity (req_id={req_id})</summary>\n\n{tail}\n</details>"
                        )
                    else:
                        tail_render = f"{__summary_text}\n\n{tail}\nreq_id={req_id}"
                    tail_line = _Txt(type="text", text=tail_render)
                    # Also emit a single-line activity summary for log watchers
                    from src.utils.response_envelope import mcp_call_summary as __mcp_summary_builder
                    __mcp_summary_line = __mcp_summary_builder(
                        tool=name,
                        status=__status_label,
                        step_no=__step_no,
                        total_steps=__total_steps,
                        duration_sec=__total_dur,
                        model=__model_used,
                        tokens=__tokens,
                        continuation_id=__cid,
                        expert_enabled=__expert_status,
                        req_id=req_id,
                    )

                    # Force-first option for renderers that only show the first block
                    if _env_true("EX_ACTIVITY_FORCE_FIRST", "false"):
                        # If a summary was inserted at index 0, place tail right after it; else at 0
                        insert_pos = 1 if (len(result) > 0 and isinstance(result[0], _Txt)) else 0
                        result.insert(insert_pos, tail_line)
                    else:
                        if _env_true("EX_ACTIVITY_TAIL_LAST", "true"):
                            result.append(tail_line)
                        else:
                            insert_at = max(0, len(result) - 1)
                            result.insert(insert_at, tail_line)
                except Exception:
                    pass

                # (Tail injection moved to unconditional section after this block)
                # Optional JSONL mirror of boundary tool-completed events
                try:
                    from utils.tool_events import ToolCallEvent as __Evt, ToolEventSink as __Sink
                    if _env_true("EX_MIRROR_ACTIVITY_TO_JSONL", "false"):
                        try:
                            __evt2 = __Evt(provider="boundary", tool_name=name, args={"event": "TOOL_COMPLETED", "req_id": req_id})
                            __evt2.end(ok=True)
                            __Sink().record(__evt2)
                        except Exception:
                            pass
                except Exception:
                    pass

        except Exception:
            pass

        # Log completion to activity file
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            # Dynamically re-enable if env now permits
            if getattr(mcp_activity_logger, "disabled", False) and _env_true("ACTIVITY_LOG", "true"):
                mcp_activity_logger.disabled = False
            mcp_activity_logger.info(f"TOOL_COMPLETED: {name} req_id={req_id}")
            # Emit TOOL_SUMMARY with lightweight fields for UI watchers
            try:
                progress_log = get_progress_log()
                prog_count = len(progress_log) if progress_log else 0
            except Exception:
                prog_count = 0
            mcp_activity_logger.info(f"TOOL_SUMMARY: name={name} req_id={req_id} progress={prog_count}")
            try:
                if '__mcp_summary_line' in locals() and __mcp_summary_line:
                    mcp_activity_logger.info(__mcp_summary_line)
            except Exception:
                pass
        except Exception:
            pass

        # Session cache write-back (store compact summary)
        try:
            cont_id = arguments.get("continuation_id")
            if cont_id:
                from utils.cache import get_session_cache, make_session_key
                cache = get_session_cache()
                skey = make_session_key(cont_id)
                cached = cache.get(skey) or {}
                # Compose compact summary (non-invasive; placeholders)
                summary = cached.get("summary") or "conversation ongoing"
                files = list({*(arguments.get("files") or []), *set(cached.get("files", []))}) if (arguments.get("files") or cached.get("files")) else cached.get("files", [])
                last_model = arguments.get("_resolved_model_name") or cached.get("last_model")
                cache.set(skey, {"summary": summary, "files": files, "last_model": last_model})
                count, max_items = cache.stats()
                logger.debug(f"[CACHE] write-back for {skey}; size={count}/{max_items}")
        except Exception as _e:
            logger.debug(f"[CACHE] write-back skipped/failed: {_e}")

        return result

    # Handle unknown tool requests gracefully
    else:
        # Suggest close tool names (env-gated)
        try:
            if _env_true("SUGGEST_TOOL_ALIASES", "true"):
                from difflib import get_close_matches
                cand = get_close_matches(name, list(TOOLS.keys()), n=1, cutoff=0.6)
                if cand:
                    suggestion = cand[0]
                    desc = TOOLS[suggestion].get_description() if suggestion in TOOLS else ""
                    return [TextContent(type="text", text=f"Unknown tool: {name}. Did you mean: {suggestion}? {desc}")]
        except Exception:
            pass
        return [TextContent(type="text", text=f"Unknown tool: {name}")]



def parse_model_option(model_string: str) -> tuple[str, Optional[str]]:
    """
    Parse model:option format into model name and option.

    Handles different formats:
    - OpenRouter models: preserve :free, :beta, :preview suffixes as part of model name
    - Ollama/Custom models: split on : to extract tags like :latest
    - Consensus stance: extract options like :for, :against

    Args:
        model_string: String that may contain "model:option" format

    Returns:
        tuple: (model_name, option) where option may be None
    """
    if ":" in model_string and not model_string.startswith("http"):  # Avoid parsing URLs
        # Check if this looks like an OpenRouter model (contains /)
        if "/" in model_string and model_string.count(":") == 1:
            # Could be openai/gpt-4:something - check what comes after colon
            parts = model_string.split(":", 1)
            suffix = parts[1].strip().lower()

            # Known OpenRouter suffixes to preserve
            if suffix in ["free", "beta", "preview"]:
                return model_string.strip(), None

        # For other patterns (Ollama tags, consensus stances), split normally
        parts = model_string.split(":", 1)
        model_name = parts[0].strip()
        model_option = parts[1].strip() if len(parts) > 1 else None
        return model_name, model_option
    return model_string.strip(), None


def get_follow_up_instructions(current_turn_count: int, max_turns: int = None) -> str:
    """
    Generate dynamic follow-up instructions based on conversation turn count.

    Args:
        current_turn_count: Current number of turns in the conversation
        max_turns: Maximum allowed turns before conversation ends (defaults to MAX_CONVERSATION_TURNS)

    Returns:
        Follow-up instructions to append to the tool prompt
    """
    if max_turns is None:
        from utils.conversation_memory import MAX_CONVERSATION_TURNS

        max_turns = MAX_CONVERSATION_TURNS

    if current_turn_count >= max_turns - 1:
        # We're at or approaching the turn limit - no more follow-ups
        return """
IMPORTANT: This is approaching the final exchange in this conversation thread.
Do NOT include any follow-up questions in your response. Provide your complete
final analysis and recommendations."""
    else:
        # Normal follow-up instructions
        remaining_turns = max_turns - current_turn_count - 1
        return f"""

CONVERSATION CONTINUATION: You can continue this discussion with Claude! ({remaining_turns} exchanges remaining)

Feel free to ask clarifying questions or suggest areas for deeper exploration naturally within your response.
If something needs clarification or you'd benefit from additional context, simply mention it conversationally.

IMPORTANT: When you suggest follow-ups or ask questions, you MUST explicitly instruct Claude to use the continuation_id
to respond. Use clear, direct language based on urgency:

For optional follow-ups: "Please continue this conversation using the continuation_id from this response if you'd "
"like to explore this further."

For needed responses: "Please respond using the continuation_id from this response - your input is needed to proceed."

For essential/critical responses: "RESPONSE REQUIRED: Please immediately continue using the continuation_id from "
"this response. Cannot proceed without your clarification/input."

This ensures Claude knows both HOW to maintain the conversation thread AND whether a response is optional, "
"needed, or essential.

The tool will automatically provide a continuation_id in the structured response that Claude can use in subsequent
tool calls to maintain full conversation context across multiple exchanges.

Remember: Only suggest follow-ups when they would genuinely add value to the discussion, and always instruct "
"Claude to use the continuation_id when you do."""


async def reconstruct_thread_context(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Reconstruct conversation context for stateless-to-stateful thread continuation.

    This is a critical function that transforms the inherently stateless MCP protocol into
    stateful multi-turn conversations. It loads persistent conversation state from in-memory
    storage and rebuilds complete conversation context using the sophisticated dual prioritization
    strategy implemented in the conversation memory system.

    CONTEXT RECONSTRUCTION PROCESS:

    1. THREAD RETRIEVAL: Loads complete ThreadContext from storage using continuation_id
       - Includes all conversation turns with tool attribution
       - Preserves file references and cross-tool context
       - Handles conversation chains across multiple linked threads

    2. CONVERSATION HISTORY BUILDING: Uses build_conversation_history() to create
       comprehensive context with intelligent prioritization:

       FILE PRIORITIZATION (Newest-First Throughout):
       - When same file appears in multiple turns, newest reference wins
       - File embedding prioritizes recent versions, excludes older duplicates
       - Token budget management ensures most relevant files are preserved

       CONVERSATION TURN PRIORITIZATION (Dual Strategy):
       - Collection Phase: Processes turns newest-to-oldest for token efficiency
       - Presentation Phase: Presents turns chronologically for LLM understanding
       - Ensures recent context is preserved when token budget is constrained

    3. CONTEXT INJECTION: Embeds reconstructed history into tool request arguments
       - Conversation history becomes part of the tool's prompt context
       - Files referenced in previous turns are accessible to current tool
       - Cross-tool knowledge transfer is seamless and comprehensive

    4. TOKEN BUDGET MANAGEMENT: Applies model-specific token allocation
       - Balances conversation history vs. file content vs. response space
       - Gracefully handles token limits with intelligent exclusion strategies
       - Preserves most contextually relevant information within constraints

    CROSS-TOOL CONTINUATION SUPPORT:
    This function enables seamless handoffs between different tools:
    - Analyze tool â†’ Debug tool: Full file context and analysis preserved
    - Chat tool â†’ CodeReview tool: Conversation context maintained
    - Any tool â†’ Any tool: Complete cross-tool knowledge transfer

    ERROR HANDLING & RECOVERY:
    - Thread expiration: Provides clear instructions for conversation restart
    - Storage unavailability: Graceful degradation with error messaging
    - Invalid continuation_id: Security validation and user-friendly errors

    Args:
        arguments: Original request arguments dictionary containing:
                  - continuation_id (required): UUID of conversation thread to resume
                  - Other tool-specific arguments that will be preserved

    Returns:
        dict[str, Any]: Enhanced arguments dictionary with conversation context:
        - Original arguments preserved
        - Conversation history embedded in appropriate format for tool consumption
        - File context from previous turns made accessible
        - Cross-tool knowledge transfer enabled

    Raises:
        ValueError: When continuation_id is invalid, thread not found, or expired
                   Includes user-friendly recovery instructions

    Performance Characteristics:
        - O(1) thread lookup in memory
        - O(n) conversation history reconstruction where n = number of turns
        - Intelligent token budgeting prevents context window overflow
        - Optimized file deduplication minimizes redundant content

    Example Usage Flow:
        1. Claude: "Continue analyzing the security issues" + continuation_id
        2. reconstruct_thread_context() loads previous analyze conversation
        3. Debug tool receives full context including previous file analysis
        4. Debug tool can reference specific findings from analyze tool
        5. Natural cross-tool collaboration without context loss
    """
    from utils.conversation_memory import add_turn, build_conversation_history, get_thread

    continuation_id = arguments["continuation_id"]

    # Get thread context from storage
    logger.debug(f"[CONVERSATION_DEBUG] Looking up thread {continuation_id} in storage")
    context = get_thread(continuation_id)
    if not context:
        logger.warning(f"Thread not found: {continuation_id}")
        logger.debug(f"[CONVERSATION_DEBUG] Thread {continuation_id} not found in storage or expired")

        # Log to activity file for monitoring
        try:
            mcp_activity_logger = logging.getLogger("mcp_activity")
            mcp_activity_logger.info(f"CONVERSATION_ERROR: Thread {continuation_id} not found or expired")
        except Exception:
            pass

        # Return error asking Claude to restart conversation with full context
        raise ValueError(
            f"Conversation thread '{continuation_id}' was not found or has expired. "
            f"This may happen if the conversation was created more than 3 hours ago or if the "
            f"server was restarted. "
            f"Please restart the conversation by providing your full question/prompt without the "
            f"continuation_id parameter. "
            f"This will create a new conversation thread that can continue with follow-up exchanges."
        )


    # Enforce session-scoped conversations if enabled
    try:
        from utils.client_info import get_current_session_fingerprint

        def _env_true(name: str, default: str = "false") -> bool:
            return str(os.getenv(name, default)).strip().lower() in {"1", "true", "yes", "on"}

        strict_scope = _env_true("EX_SESSION_SCOPE_STRICT", "false")
        allow_cross = _env_true("EX_SESSION_SCOPE_ALLOW_CROSS_SESSION", "false")
        current_fp = get_current_session_fingerprint(arguments)
        stored_fp = getattr(context, "session_fingerprint", None)
        if strict_scope and stored_fp and current_fp and stored_fp != current_fp and not allow_cross:
            # Log to activity for diagnostics
            try:
                mcp_activity_logger = logging.getLogger("mcp_activity")
                mcp_activity_logger.warning(
                    f"CONVERSATION_SCOPE_BLOCK: thread={continuation_id} stored_fp={stored_fp} current_fp={current_fp}"
                )
            except Exception:
                pass
            raise ValueError(
                "This continuation_id belongs to a different client session. "
                "To avoid accidental cross-window sharing, session-scoped conversations are enabled. "
                "Start a fresh conversation (omit continuation_id) or explicitly allow cross-session use by setting "
                "EX_SESSION_SCOPE_ALLOW_CROSS_SESSION=true."
            )
        # Soft warn if cross-session allowed
        if stored_fp and current_fp and stored_fp != current_fp and allow_cross:
            try:
                mcp_activity_logger = logging.getLogger("mcp_activity")
                mcp_activity_logger.info(
                    f"CONVERSATION_SCOPE_WARN: cross-session continuation allowed thread={continuation_id}"
                )
            except Exception:
                pass
    except Exception:
        # Never hard-fail scope checks; proceed if anything goes wrong
        pass

    # Add user's new input to the conversation
    user_prompt = arguments.get("prompt", "")
    if user_prompt:
        # Capture files referenced in this turn
        user_files = arguments.get("files", [])
        logger.debug(f"[CONVERSATION_DEBUG] Adding user turn to thread {continuation_id}")
        from utils.token_utils import estimate_tokens

        user_prompt_tokens = estimate_tokens(user_prompt)
        logger.debug(
            f"[CONVERSATION_DEBUG] User prompt length: {len(user_prompt)} chars (~{user_prompt_tokens:,} tokens)"
        )
        logger.debug(f"[CONVERSATION_DEBUG] User files: {user_files}")
        success = add_turn(continuation_id, "user", user_prompt, files=user_files)
        if not success:
            logger.warning(f"Failed to add user turn to thread {continuation_id}")
            logger.debug("[CONVERSATION_DEBUG] Failed to add user turn - thread may be at turn limit or expired")
        else:
            logger.debug(f"[CONVERSATION_DEBUG] Successfully added user turn to thread {continuation_id}")

    # Create model context early to use for history building
    from utils.model_context import ModelContext

    # Check if we should use the model from the previous conversation turn
    model_from_args = arguments.get("model")
    if not model_from_args and context.turns:
        # Find the last assistant turn to get the model used
        for turn in reversed(context.turns):
            if turn.role == "assistant" and turn.model_name:
                arguments["model"] = turn.model_name
                logger.debug(f"[CONVERSATION_DEBUG] Using model from previous turn: {turn.model_name}")
                break

    model_context = ModelContext.from_arguments(arguments)

    # Build conversation history with model-specific limits
    logger.debug(f"[CONVERSATION_DEBUG] Building conversation history for thread {continuation_id}")
    logger.debug(f"[CONVERSATION_DEBUG] Thread has {len(context.turns)} turns, tool: {context.tool_name}")
    logger.debug(f"[CONVERSATION_DEBUG] Using model: {model_context.model_name}")
    conversation_history, conversation_tokens = build_conversation_history(context, model_context)
    logger.debug(f"[CONVERSATION_DEBUG] Conversation history built: {conversation_tokens:,} tokens")
    logger.debug(
        f"[CONVERSATION_DEBUG] Conversation history length: {len(conversation_history)} chars (~{conversation_tokens:,} tokens)"
    )

    # Add dynamic follow-up instructions based on turn count
    follow_up_instructions = get_follow_up_instructions(len(context.turns))
    logger.debug(f"[CONVERSATION_DEBUG] Follow-up instructions added for turn {len(context.turns)}")

    # All tools now use standardized 'prompt' field
    original_prompt = arguments.get("prompt", "")
    logger.debug("[CONVERSATION_DEBUG] Extracting user input from 'prompt' field")
    original_prompt_tokens = estimate_tokens(original_prompt) if original_prompt else 0
    logger.debug(
        f"[CONVERSATION_DEBUG] User input length: {len(original_prompt)} chars (~{original_prompt_tokens:,} tokens)"
    )

    # Merge original context with new prompt and follow-up instructions
    if conversation_history:
        enhanced_prompt = (
            f"{conversation_history}\n\n=== NEW USER INPUT ===\n{original_prompt}\n\n{follow_up_instructions}"
        )
    else:
        enhanced_prompt = f"{original_prompt}\n\n{follow_up_instructions}"

    # Update arguments with enhanced context and remaining token budget
    enhanced_arguments = arguments.copy()

    # Store the enhanced prompt in the prompt field
    enhanced_arguments["prompt"] = enhanced_prompt
    # Store the original user prompt separately for size validation
    enhanced_arguments["_original_user_prompt"] = original_prompt
    logger.debug("[CONVERSATION_DEBUG] Storing enhanced prompt in 'prompt' field")
    logger.debug("[CONVERSATION_DEBUG] Storing original user prompt in '_original_user_prompt' field")

    # Calculate remaining token budget based on current model
    # (model_context was already created above for history building)
    token_allocation = model_context.calculate_token_allocation()

    # Calculate remaining tokens for files/new content
    # History has already consumed some of the content budget
    remaining_tokens = token_allocation.content_tokens - conversation_tokens
    enhanced_arguments["_remaining_tokens"] = max(0, remaining_tokens)  # Ensure non-negative
    enhanced_arguments["_model_context"] = model_context  # Pass context for use in tools

    logger.debug("[CONVERSATION_DEBUG] Token budget calculation:")
    logger.debug(f"[CONVERSATION_DEBUG]   Model: {model_context.model_name}")
    logger.debug(f"[CONVERSATION_DEBUG]   Total capacity: {token_allocation.total_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Content allocation: {token_allocation.content_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Conversation tokens: {conversation_tokens:,}")
    logger.debug(f"[CONVERSATION_DEBUG]   Remaining tokens: {remaining_tokens:,}")

    # Merge original context parameters (files, etc.) with new request
    if context.initial_context:
        logger.debug(f"[CONVERSATION_DEBUG] Merging initial context with {len(context.initial_context)} parameters")
        for key, value in context.initial_context.items():
            if key not in enhanced_arguments and key not in ["temperature", "thinking_mode", "model"]:
                enhanced_arguments[key] = value
                logger.debug(f"[CONVERSATION_DEBUG] Merged initial context param: {key}")

    logger.info(f"Reconstructed context for thread {continuation_id} (turn {len(context.turns)})")
    logger.debug(f"[CONVERSATION_DEBUG] Final enhanced arguments keys: {list(enhanced_arguments.keys())}")

    # Debug log files in the enhanced arguments for file tracking
    if "files" in enhanced_arguments:
        logger.debug(f"[CONVERSATION_DEBUG] Final files in enhanced arguments: {enhanced_arguments['files']}")

    # Log to activity file for monitoring
    try:
        mcp_activity_logger = logging.getLogger("mcp_activity")
        mcp_activity_logger.info(
            f"CONVERSATION_CONTINUATION: Thread {continuation_id} turn {len(context.turns)} - "
            f"{len(context.turns)} previous turns loaded"
        )
    except Exception:
        pass

    return enhanced_arguments


@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """
    List all available prompts for Claude Code shortcuts.

    This handler returns prompts that enable shortcuts like /ex:thinkdeeper.
    We automatically generate prompts from all tools (1:1 mapping) plus add
    a few marketing aliases with richer templates for commonly used tools.

    Returns:
        List of Prompt objects representing all available prompts
    """
    logger.debug("MCP client requested prompt list")
    prompts = []

    # Add a prompt for each tool with rich templates
    for tool_name, tool in TOOLS.items():
        if tool_name in PROMPT_TEMPLATES:
            # Use the rich template
            template_info = PROMPT_TEMPLATES[tool_name]
            prompts.append(
                Prompt(
                    name=template_info["name"],
                    description=template_info["description"],
                    arguments=[],  # MVP: no structured args
                )
            )
        else:
            # Fallback for any tools without templates (shouldn't happen)
            prompts.append(
                Prompt(
                    name=tool_name,
                    description=f"Use {tool.name} tool",
                    arguments=[],
                )
            )

    # Add special "continue" prompt
    prompts.append(
        Prompt(
            name="continue",
            description="Continue the previous conversation using the chat tool",
            arguments=[],
        )
    )

    logger.debug(f"Returning {len(prompts)} prompts to MCP client")
    return prompts


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, Any] = None) -> GetPromptResult:
    """
    Get prompt details and generate the actual prompt text.

    This handler is called when a user invokes a prompt (e.g., /ex:thinkdeeper or /ex:chat:gpt5).
    It generates the appropriate text that Claude will then use to call the
    underlying tool.

    Supports structured prompt names like "chat:gpt5" where:
    - "chat" is the tool name
    - "gpt5" is the model to use

    Args:
        name: The name of the prompt to execute (can include model like "chat:gpt5")
        arguments: Optional arguments for the prompt (e.g., model, thinking_mode)

    Returns:
        GetPromptResult with the prompt details and generated message

    Raises:
        ValueError: If the prompt name is unknown
    """
    logger.debug(f"MCP client requested prompt: {name} with args: {arguments}")

    # Handle special "continue" case
    if name.lower() == "continue":
        # This is "/ex:continue" - use chat tool as default for continuation
        tool_name = "chat"
        template_info = {
            "name": "continue",
            "description": "Continue the previous conversation",
            "template": "Continue the conversation",
        }
        logger.debug("Using /ex:continue - defaulting to chat tool")
    else:
        # Find the corresponding tool by checking prompt names
        tool_name = None
        template_info = None

        # Check if it's a known prompt name
        for t_name, t_info in PROMPT_TEMPLATES.items():
            if t_info["name"] == name:
                tool_name = t_name
                template_info = t_info
                break

        # If not found, check if it's a direct tool name
        if not tool_name and name in TOOLS:
            tool_name = name
            template_info = {
                "name": name,
                "description": f"Use {name} tool",
                "template": f"Use {name}",
            }

        if not tool_name:
            logger.error(f"Unknown prompt requested: {name}")
            raise ValueError(f"Unknown prompt: {name}")

    # Get the template
    template = template_info.get("template", f"Use {tool_name}")

    # Safe template expansion with defaults
    final_model = arguments.get("model", "auto") if arguments else "auto"

    prompt_args = {
        "model": final_model,
        "thinking_mode": arguments.get("thinking_mode", "medium") if arguments else "medium",
    }

    logger.debug(f"Using model '{final_model}' for prompt '{name}'")

    # Safely format the template
    try:
        prompt_text = template.format(**prompt_args)
    except KeyError as e:
        logger.warning(f"Missing template argument {e} for prompt {name}, using raw template")
        prompt_text = template  # Fallback to raw template

    # Generate tool call instruction
    if name.lower() == "continue":
        # "/ex:continue" case
        tool_instruction = (
            f"Continue the previous conversation using the {tool_name} tool. "
            "CRITICAL: You MUST provide the continuation_id from the previous response to maintain conversation context. "
            "Additionally, you should reuse the same model that was used in the previous exchange for consistency, unless "
            "the user specifically asks for a different model name to be used."
        )
    else:
        # Simple prompt case
        tool_instruction = prompt_text

    # Optional: auto-discover models to enrich config for selector
    try:
        if AUGGIE_ACTIVE or detect_auggie_cli():
            from auggie.model_discovery import discover_models
            discovered = discover_models()
            if discovered:
                logging.info(f"Discovered models: {len(discovered)} candidates")
    except Exception:
        pass

    return GetPromptResult(
        prompt=Prompt(
            name=name,
            description=template_info["description"],
            arguments=[],
        ),
        messages=[
            PromptMessage(
                role="user",
                content={"type": "text", "text": tool_instruction},
            )
        ],
    )



async def main():
    """
    Main entry point for the MCP server.

    Initializes the Gemini API configuration and starts the server using
    stdio transport. The server will continue running until the client
    disconnects or an error occurs.

    The server communicates via standard input/output streams using the
    MCP protocol's JSON-RPC message format.
    """
    # Centralized config validation (non-fatal, stderr only)
    # Enabled by default; set ENABLE_CONFIG_VALIDATOR=false to skip
    if _env_true("ENABLE_CONFIG_VALIDATOR", "true"):
        try:
            from utils.config_bootstrap import ServerConfig
            # trigger validation; result not used
            _ = ServerConfig.load_and_validate()
        except Exception as _e:
            logger.warning(f"CONFIG VALIDATION failed: {_e}")

    # Validate and configure providers based on available API keys
    configure_providers()

    # Start Prometheus metrics endpoint if enabled
    try:
        from utils.metrics import init_metrics_server_if_enabled
        init_metrics_server_if_enabled()
    except Exception as _e:
        logger.debug(f"Metrics init skipped/failed: {_e}")

    # Router preflight (listmodels + trivial chat), env-gated
    try:
        if _env_true("VALIDATE_PROVIDERS_ON_START", "true"):
            from src.router.service import RouterService  # lazy import
            RouterService().preflight()
    except Exception as _e:
        logger.debug(f"Router preflight skipped/failed: {_e}")

    # Optional DEFAULT_MODEL availability validation (env-gated)
    try:
        if _env_true("VALIDATE_DEFAULT_MODEL", "true"):
            from src.providers.registry import ModelProviderRegistry
            if ModelProviderRegistry.get_provider_for_model(DEFAULT_MODEL) is None:
                logger.warning(
                    "DEFAULT_MODEL '%s' not available with current providers; using auto selection or explicit per-tool model",
                    DEFAULT_MODEL,
                )
    except Exception as _e:
        logger.debug(f"Default model validation skipped/failed: {_e}")

    # Log startup message
    logger.info("EX MCP Server starting up...")
    logger.info(f"Log level: {log_level}")

    # Note: MCP client info will be logged during the protocol handshake
    # (when handle_list_tools is called)

    # Log current model mode
    from config import IS_AUTO_MODE

    if IS_AUTO_MODE:
        logger.info("Model mode: AUTO (Claude will select the best model for each task)")
    else:
        logger.info(f"Model mode: Fixed model '{DEFAULT_MODEL}'")

    # Import here to avoid circular imports
    from config import DEFAULT_THINKING_MODE_THINKDEEP

    logger.info(f"Default thinking mode (ThinkDeep): {DEFAULT_THINKING_MODE_THINKDEEP}")

    logger.info(f"Available tools: {list(TOOLS.keys())}")
    logger.info("Server ready - waiting for tool requests...")

    # Run the server using stdio transport (standard input/output)
    # This allows the server to be launched by MCP clients as a subprocess
    async with stdio_server() as (read_stream, write_stream):
        # Wire up best-effort MCP notifier for progress messages
        try:
            import asyncio as _asyncio  # local import to avoid module-level cost

            async def _notify_progress(msg: str, level: str = "info"):
                """Send live progress to MCP clients via notifications, with fallbacks.
                - Prefer MCP notifications/message if supported by the Python SDK
                - Fallback to server.request_context.session.send_log_message if available
                - Always mirror to the server's internal logger for UIs that surface it
                """
                # Try official logging notification API (newer SDKs)
                try:
                    if hasattr(server, "send_logging_message"):
                        await server.send_logging_message({"level": level, "data": f"[PROGRESS] {msg}"})
                    else:
                        # Older SDKs: request_context.session.send_log_message
                        rc = getattr(server, "request_context", None)
                        sess = getattr(rc, "session", None) if rc else None
                        if sess and hasattr(sess, "send_log_message"):
                            await sess.send_log_message(level=level, data=f"[PROGRESS] {msg}")
                except Exception:
                    # Never fail tool execution due to progress emission
                    pass
                finally:
                    # Mirror to internal logger as a universal fallback
                    try:
                        server._logger.log({"debug":10,"info":20,"warning":30,"error":40}.get((level or "info"),20), f"[PROGRESS] {msg}")
                    except Exception:
                        pass

            set_mcp_notifier(_notify_progress)
        except Exception:
            pass

        # Emit a clear handshake breadcrumb on stderr for CLI debugging (opt-in)
        try:
            if _stderr_breadcrumbs():
                print("[ex-mcp] stdio_server started; awaiting MCP handshake...", file=sys.stderr)
        except Exception:
            pass
        # Run server with standard capabilities; avoid advertising experimental fields
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=os.getenv("MCP_SERVER_NAME", "EX MCP Server"),
                server_version=__version__,
                capabilities=ServerCapabilities(
                    tools=ToolsCapability(),  # Advertise tool support capability
                    prompts=PromptsCapability(),  # Advertise prompt support capability
                ),
            ),
        )


def run():
    """Console script entry point for ex-mcp-server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle graceful shutdown
        pass


if __name__ == "__main__":
    run()

