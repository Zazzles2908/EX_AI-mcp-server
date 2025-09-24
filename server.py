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

# Environment and configuration setup
def _env_true(key: str, default: str = "false") -> bool:
    """Check if environment variable is set to a truthy value."""
    return os.getenv(key, default).lower() in ("true", "1", "yes", "on")

def _write_wrapper_error(text: str) -> None:
    """Write error message to stderr with proper formatting."""
    try:
        print(f"[ex-mcp] {text}", file=sys.stderr, flush=True)
    except Exception:
        pass

# Bootstrap and environment loading
if _env_true("EX_MCP_BOOTSTRAP_DEBUG"):
    print("[ex-mcp] bootstrap starting (pid=%s, py=%s)" % (os.getpid(), sys.executable), file=sys.stderr)

# Load environment variables
try:
    from dotenv import load_dotenv
    
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        if _env_true("EX_MCP_BOOTSTRAP_DEBUG"):
            print(f"[ex-mcp] loaded .env from {env_path}", file=sys.stderr)
    else:
        if _env_true("EX_MCP_BOOTSTRAP_DEBUG"):
            print(f"[ex-mcp] no .env file found at {env_path}", file=sys.stderr)
            
except ImportError:
    if _env_true("EX_MCP_BOOTSTRAP_DEBUG"):
        print("[ex-mcp] python-dotenv not available, skipping .env load", file=sys.stderr)
except Exception as dotenv_err:
    msg = f"[ex-mcp] dotenv load failed: {dotenv_err}"
    _write_wrapper_error(msg)

def _hot_reload_env() -> None:
    """Hot reload environment variables from .env file."""
    try:
        from dotenv import load_dotenv as _ld
        env_path = Path(__file__).parent / ".env"
        if env_path.exists():
            _ld(env_path, override=True)
    except Exception:
        # Never let hot-reload break a tool call
        pass

# Import MCP components
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        GetPromptResult,
        Prompt,
        PromptsCapability,
        ServerCapabilities,
        TextContent,
        Tool,
        ToolsCapability,
    )
    
    # MCP SDK compatibility
    try:
        from mcp.types import ToolAnnotations
    except ImportError:
        ToolAnnotations = None

except ImportError as e:
    _write_wrapper_error(f"Failed to import MCP components: {e}")
    sys.exit(1)

# Import tools and configuration
from config import __version__
from tools import (
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
    SelfCheckTool,
    TestGenTool,
    ThinkDeepTool,
    TracerTool,
    VersionTool,
)

# Import modular server components
from src.server.providers import configure_providers
from src.server.tools import filter_disabled_tools
from src.server.handlers import (
    handle_call_tool,
    handle_get_prompt,
    handle_list_prompts,
    handle_list_tools,
)

# Auggie integration check
AUGGIE_ACTIVE = _env_true("AUGGIE_ACTIVE")
AUGGIE_WRAPPERS_AVAILABLE = False

try:
    from auggie.wrappers import AUGGIE_WRAPPERS_AVAILABLE
except ImportError:
    pass

def detect_auggie_cli() -> bool:
    """Detect if running under Auggie CLI."""
    return any(
        "auggie" in arg.lower() or "aug" in arg.lower()
        for arg in sys.argv
    )

# Logging configuration
class LocalTimeFormatter(logging.Formatter):
    """Custom formatter that uses local time instead of UTC."""
    
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s,%03d" % (t, record.msecs)
        return s

class JsonLineFormatter(logging.Formatter):
    """JSON line formatter for structured logging."""
    
    def format(self, record):
        import json
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "tool_name"):
            log_entry["tool_name"] = record.tool_name
        if hasattr(record, "model"):
            log_entry["model"] = record.model
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id
            
        return json.dumps(log_entry)

# Configure logging
def setup_logging():
    """Set up logging configuration."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create logs directory
    logs_dir = Path(".logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            RotatingFileHandler(
                logs_dir / "server.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
    
    # Set up structured logging for metrics
    metrics_logger = logging.getLogger("metrics")
    metrics_handler = RotatingFileHandler(
        logs_dir / "metrics.jsonl",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=3
    )
    metrics_handler.setFormatter(JsonLineFormatter())
    metrics_logger.addHandler(metrics_handler)
    metrics_logger.setLevel(logging.INFO)

# Initialize logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize MCP server
server = Server("EX MCP Server")

# Tool registry
TOOLS = {
    "chat": ChatTool(),
    "thinkdeep": ThinkDeepTool(),
    "planner": PlannerTool(),
    "consensus": ConsensusTool(),
    "codereview": CodeReviewTool(),
    "precommit": PrecommitTool(),
    "debug": DebugIssueTool(),
    "secaudit": SecauditTool(),
    "docgen": DocgenTool(),
    "analyze": AnalyzeTool(),
    "refactor": RefactorTool(),
    "tracer": TracerTool(),
    "testgen": TestGenTool(),
    "challenge": ChallengeTool(),
    "listmodels": ListModelsTool(),
    "version": VersionTool(),
    "selfcheck": SelfCheckTool(),
}

# Auggie tool registration
if (AUGGIE_ACTIVE or detect_auggie_cli()) and AUGGIE_WRAPPERS_AVAILABLE:
    logger.info("Registering Auggie-optimized tools (aug_*) alongside originals")
    
    class AugChatTool(ChatTool):
        def get_name(self) -> str: 
            return "aug_chat"
        
        def get_description(self) -> str:
            return f"[Auggie-optimized] {super().get_description()}"
    
    class AugThinkDeepTool(ThinkDeepTool):
        def get_name(self) -> str:
            return "aug_thinkdeep"
            
        def get_description(self) -> str:
            return f"[Auggie-optimized] {super().get_description()}"
    
    class AugConsensusTool(ConsensusTool):
        def get_name(self) -> str:
            return "aug_consensus"
            
        def get_description(self) -> str:
            return f"[Auggie-optimized] {super().get_description()}"
    
    # Register Auggie tools
    TOOLS.update({
        "aug_chat": AugChatTool(),
        "aug_thinkdeep": AugThinkDeepTool(), 
        "aug_consensus": AugConsensusTool(),
    })

# Global state
IS_AUTO_MODE = _env_true("EX_AUTO_MODE")
_providers_configured = False

def _ensure_providers_configured():
    """Ensure providers are configured when server is used as a module."""
    global _providers_configured
    if not _providers_configured:
        try:
            configure_providers()
            _providers_configured = True
        except Exception as e:
            logger.warning(f"Provider configuration failed: {e}")

# Register MCP handlers
@server.list_tools()
async def list_tools_handler():
    """Handle MCP list_tools requests."""
    return await handle_list_tools()

@server.call_tool()
async def call_tool_handler(name: str, arguments: dict[str, Any]):
    """Handle MCP call_tool requests."""
    _ensure_providers_configured()
    return await handle_call_tool(name, arguments)

@server.list_prompts()
async def list_prompts_handler():
    """Handle MCP list_prompts requests."""
    return await handle_list_prompts()

@server.get_prompt()
async def get_prompt_handler(name: str, arguments: dict[str, Any] = None):
    """Handle MCP get_prompt requests."""
    return await handle_get_prompt(name, arguments)

async def main():
    """Main server entry point."""
    # Configure providers
    try:
        configure_providers()
    except Exception as e:
        logger.error(f"Failed to configure providers: {e}")
        sys.exit(1)
    
    # Filter disabled tools
    global TOOLS
    TOOLS = filter_disabled_tools(TOOLS)
    
    # Set up stdio streams
    read_stream, write_stream = stdio_server()
    
    # Configure progress notifications
    try:
        from utils.progress import set_mcp_notifier
        
        async def _notify_progress(level: str, msg: str):
            try:
                # Try to emit via MCP session if available
                rc = getattr(server, "_request_context", None)
                sess = getattr(rc, "session", None) if rc else None
                if sess and hasattr(sess, "send_log_message"):
                    await sess.send_log_message(level=level, data=f"[PROGRESS] {msg}")
            except Exception:
                pass
            finally:
                # Mirror to internal logger
                try:
                    log_level = {"debug": 10, "info": 20, "warning": 30, "error": 40}.get(level, 20)
                    server._logger.log(log_level, f"[PROGRESS] {msg}")
                except Exception:
                    pass
        
        set_mcp_notifier(_notify_progress)
    except Exception:
        pass
    
    # Emit handshake breadcrumb
    try:
        if _env_true("EX_MCP_STDERR_BREADCRUMBS"):
            print("[ex-mcp] stdio_server started; awaiting MCP handshake...", file=sys.stderr)
    except Exception:
        pass
    
    # Run server
    await server.run(
        read_stream,
        write_stream,
        InitializationOptions(
            server_name=os.getenv("MCP_SERVER_NAME", "EX MCP Server"),
            server_version=__version__,
            capabilities=ServerCapabilities(
                tools=ToolsCapability(),
                prompts=PromptsCapability(),
            ),
        ),
    )

def run():
    """Console script entry point for ex-mcp-server."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
