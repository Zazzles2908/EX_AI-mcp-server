"""
Tool Filtering and Management Module

This module handles tool filtering, validation, and configuration
for the EX MCP Server tool registry.
"""

import logging
from typing import Any, Dict, Set

logger = logging.getLogger(__name__)

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


