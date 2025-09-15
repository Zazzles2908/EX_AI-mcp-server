"""Lean Tool Registry for Zen MCP.

Build the tool set once at server startup, honoring env flags:
- LEAN_MODE=true|false (default false)
- LEAN_TOOLS=comma,list (when LEAN_MODE=true, overrides default lean set)
- DISABLED_TOOLS=comma,list (always excluded)

Always expose light utility tools (listmodels, version) for diagnostics.
Provide helpful error if a disabled tool is invoked.
"""
from __future__ import annotations

import os
from typing import Any, Dict

# Map tool names to import paths (module, class)
TOOL_MAP: Dict[str, tuple[str, str]] = {
    # Core
    "chat": ("src.tools.chat", "ChatTool"),
    "analyze": ("tools.analyze", "AnalyzeTool"),
    "debug": ("src.tools.debug", "DebugIssueTool"),
    "codereview": ("tools.codereview", "CodeReviewTool"),
    "refactor": ("tools.refactor", "RefactorTool"),
    "secaudit": ("tools.secaudit", "SecauditTool"),
    "planner": ("src.tools.planner", "PlannerTool"),
    "tracer": ("tools.tracer", "TracerTool"),
    "testgen": ("tools.testgen", "TestGenTool"),
    "consensus": ("tools.consensus", "ConsensusTool"),
    "thinkdeep": ("tools.thinkdeep", "ThinkDeepTool"),
    "docgen": ("tools.docgen", "DocgenTool"),
    # Utilities (always on)
    "version": ("tools.version", "VersionTool"),
    "listmodels": ("tools.listmodels", "ListModelsTool"),
    "self-check": ("tools.selfcheck", "SelfCheckTool"),
    # Web tools removed: internet access disabled in production build

    # Precommit and Challenge utilities
    "precommit": ("tools.precommit", "PrecommitTool"),
    "challenge": ("tools.challenge", "ChallengeTool"),
    # Orchestrators (aliases map to autopilot) - RE-ENABLED after adding prepare_prompt method
    "orchestrate_auto": ("tools.autopilot", "AutopilotTool"),
    # Kimi utilities
    "kimi_upload_and_extract": ("tools.kimi_upload", "KimiUploadAndExtractTool"),
    "kimi_multi_file_chat": ("tools.kimi_upload", "KimiMultiFileChatTool"),  # RE-ENABLED after implementing abstract methods
    # GLM utilities - RE-ENABLED after implementing abstract methods
    "glm_upload_file": ("tools.glm_files", "GLMUploadFileTool"),
    "glm_multi_file_chat": ("tools.glm_files", "GLMMultiFileChatTool"),
    # GLM Agent APIs - RE-ENABLED after installing requests dependency
    "glm_agent_chat": ("tools.glm_agents", "GLMAgentChatTool"),
    "glm_agent_get_result": ("tools.glm_agents", "GLMAgentGetResultTool"),
    "await_result": ("tools.await_result", "AwaitResultTool"),

    "glm_agent_conversation": ("tools.glm_agents", "GLMAgentConversationTool"),
    # Kimi chat with tools/tool_choice
    "kimi_chat_with_tools": ("tools.kimi_tools_chat", "KimiChatWithToolsTool"),
    # Diagnostics
    "provider_capabilities": ("tools.provider_capabilities", "ProviderCapabilitiesTool"),
    # Observability helpers
    "toolcall_log_tail": ("tools.toolcall_log_tail", "ToolcallLogTail"),  # RE-ENABLED after implementing abstract methods
    "activity": ("tools.activity", "ActivityTool"),
    # Health
    "health": ("tools.health", "HealthTool"),
    # Context Performance Monitoring
    "context_performance": ("tools.context_performance", "ContextPerformanceTool"),
    # Status alias (friendly summary) - RE-ENABLED after adding prepare_prompt method
    "status": ("tools.status", "StatusTool"),
    # Autopilot orchestrator (opt-in) - RE-ENABLED after adding prepare_prompt method
    "autopilot": ("tools.autopilot", "AutopilotTool"),
    # Browse orchestrator (alias to autopilot) - RE-ENABLED after adding prepare_prompt method
    "browse_orchestrator": ("tools.autopilot", "AutopilotTool"),

}
# Visibility map for tools: 'core' | 'advanced' | 'hidden'
TOOL_VISIBILITY = {
    # Core verbs
    "status": "core",  # RE-ENABLED
    "chat": "core",
    "planner": "core",
    "thinkdeep": "core",
    "analyze": "core",
    "codereview": "core",
    "refactor": "core",
    "testgen": "core",
    "debug": "core",
    "autopilot": "core",  # RE-ENABLED
    # Auxiliary (advanced)
    "provider_capabilities": "advanced",
    "listmodels": "advanced",
    "activity": "advanced",
    "version": "advanced",
    "context_performance": "advanced",
    "kimi_chat_with_tools": "advanced",
    "kimi_upload_and_extract": "advanced",
    "glm_agent_chat": "advanced",  # RE-ENABLED
    "glm_agent_get_result": "advanced",  # RE-ENABLED
    "glm_agent_conversation": "advanced",  # RE-ENABLED
    "glm_upload_file": "advanced",  # RE-ENABLED
    "glm_multi_file_chat": "advanced",  # RE-ENABLED
    "await_result": "advanced",
    "consensus": "advanced",
    "docgen": "advanced",
    "secaudit": "advanced",
    "tracer": "advanced",
    "precommit": "advanced",
    # Hidden/internal
    "toolcall_log_tail": "hidden",  # RE-ENABLED
    "health": "hidden",
    # "browse_orchestrator": "hidden",  # DISABLED
    # "orchestrate_auto": "hidden",  # DISABLED
}


DEFAULT_LEAN_TOOLS = {
    "chat",
    "analyze",
    "planner",
    "thinkdeep",
    "version",
    "listmodels",
}

# Compact UI profile: limit visible/advertised tools to <=12 while preserving functionality
# Keep consensus explicitly in the compact set per product requirement.
COMPACT_VISIBLE_TOOLS = {
    # Core user-facing verbs (<=12)
    "chat",          # Ask/Chat
    "analyze",       # Analyze Code
    "codereview",    # Review Code
    "debug",         # Debug Issue
    "refactor",      # Refactor Code
    "testgen",       # Generate Tests
    "planner",       # Plan Tasks
    "secaudit",      # Secure/Audit
    "precommit",     # Precommit Check
    "tracer",        # Trace/Explore
    "consensus",     # Consensus (explicitly included)
    "status",        # Status/Models (hub/summary)
}

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}
        self._errors: Dict[str, str] = {}

    def _load_tool(self, name: str) -> None:
        module_path, class_name = TOOL_MAP[name]
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            self._tools[name] = cls()
        except Exception as e:
            # Use structured error handling for tool loading failures
            try:
                from utils.error_handling import ErrorClassifier
                friendly_error = ErrorClassifier.create_user_friendly_error(e, f"loading {name} tool")
                self._errors[name] = friendly_error.user_message
                # Log technical details for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to load tool {name}: {friendly_error.technical_details}")
            except Exception:
                # Fallback to original error handling
                self._errors[name] = str(e)

    def build_tools(self) -> None:
        disabled = {t.strip().lower() for t in os.getenv("DISABLED_TOOLS", "").split(",") if t.strip()}
        ui_profile = os.getenv("UI_PROFILE", "").strip().lower()
        lean_mode = os.getenv("LEAN_MODE", "false").strip().lower() == "true"

        # Always load ALL tools (minus disabled) to preserve full functionality.
        # UI profile will only affect what is advertised via list_descriptors().
        active = set(TOOL_MAP.keys())

        # Ensure utilities are always on (diagnostics)
        active.update({"version", "listmodels"})

        # Remove disabled
        active = {t for t in active if t not in disabled}

        # Gate orchestrators behind env to avoid loading errors until stable
        if os.getenv("ORCHESTRATORS_ENABLED", "false").strip().lower() != "true":
            for t in ("autopilot", "browse_orchestrator", "orchestrate_auto"):
                active.discard(t)

        # Hide diagnostics-only tools unless explicitly enabled
        if os.getenv("DIAGNOSTICS", "false").strip().lower() != "true":
            active.discard("self-check")

        # Load all active tools
        for name in sorted(active):
            self._load_tool(name)

        # Store UI profile for descriptor filtering
        self._ui_profile = ui_profile or ("compact" if lean_mode else "full")

    def get_tool(self, name: str) -> Any:
        if name in self._tools:
            return self._tools[name]
        if name in self._errors:
            raise RuntimeError(f"Tool '{name}' failed to load: {self._errors[name]}")
        raise KeyError(
            f"Tool '{name}' is not registered. It may be disabled (LEAN_MODE/DISABLED_TOOLS) or unavailable."
        )

    def list_tools(self) -> Dict[str, Any]:
        return dict(self._tools)

    def list_descriptors(self) -> Dict[str, Any]:
        """Return machine-readable descriptors filtered by UI profile.

        - compact: only advertise COMPACT_VISIBLE_TOOLS (<=12) to keep UI simple.
        - full: advertise all loaded tools.
        Tools remain loadable internally regardless of advertisement status.
        """
        profile = getattr(self, "_ui_profile", "full")
        visible_set = set(self._tools.keys()) if profile != "compact" else set(COMPACT_VISIBLE_TOOLS)

        descs: Dict[str, Any] = {}
        for name, tool in self._tools.items():
            if name not in visible_set:
                continue
            try:
                # Each tool provides a default get_descriptor()
                d = tool.get_descriptor()
                # Include minimal UI hints
                d["ui_profile"] = profile
                d["visible"] = True
                descs[name] = d
            except Exception as e:
                descs[name] = {"error": f"Failed to get descriptor: {e}", "visible": True, "ui_profile": profile}
        return descs

