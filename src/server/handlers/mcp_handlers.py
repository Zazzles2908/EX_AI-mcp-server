import sys
sys.path.append(".")
from tools import TOOLS
from src.server.tools import filter_disabled_tools
from utils.client_info import format_client_info, get_client_info_from_context
from src.providers.openrouter_registry import OpenRouterRegistry

"""
MCP Protocol Handlers Module

This module contains the main MCP protocol handlers for tools and prompts.
These handlers implement the MCP specification for tool discovery and execution.
"""

import logging
import os
from typing import Any, List
from mcp.types import Tool, Prompt, TextContent, GetPromptResult

logger = logging.getLogger(__name__)

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



