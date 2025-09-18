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
    "chat": ("tools.chat", "ChatTool"),
    "analyze": ("tools.analyze", "AnalyzeTool"),
    "debug": ("tools.debug", "DebugIssueTool"),
    "codereview": ("tools.codereview", "CodeReviewTool"),
    "refactor": ("tools.refactor", "RefactorTool"),
    "secaudit": ("tools.secaudit", "SecauditTool"),
    "planner": ("tools.planner", "PlannerTool"),
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
    # Orchestrators (aliases map to autopilot)
    "orchestrate_auto": ("tools.autopilot", "AutopilotTool"),
    # Kimi utilities
    "kimi_upload_and_extract": ("tools.kimi_upload", "KimiUploadAndExtractTool"),
    "kimi_multi_file_chat": ("tools.kimi_upload", "KimiMultiFileChatTool"),
    # GLM utilities
    "glm_upload_file": ("tools.glm_files", "GLMUploadFileTool"),
    "glm_multi_file_chat": ("tools.glm_files", "GLMMultiFileChatTool"),
    # GLM Agent APIs
    "glm_agent_chat": ("tools.glm_agents", "GLMAgentChatTool"),
    "glm_agent_get_result": ("tools.glm_agents", "GLMAgentGetResultTool"),
    "glm_agent_conversation": ("tools.glm_agents", "GLMAgentConversationTool"),
    # Kimi chat with tools/tool_choice
    "kimi_chat_with_tools": ("tools.kimi_tools_chat", "KimiChatWithToolsTool"),
    # Diagnostics
    "provider_capabilities": ("tools.provider_capabilities", "ProviderCapabilitiesTool"),
    # Observability helpers
    "toolcall_log_tail": ("tools.toolcall_log_tail", "ToolcallLogTail"),
    "activity": ("tools.activity", "ActivityTool"),
    # Health
    "health": ("tools.health", "HealthTool"),
    # Status alias (friendly summary)
    "status": ("tools.status", "StatusTool"),
    # Autopilot orchestrator (opt-in)
    "autopilot": ("tools.autopilot", "AutopilotTool"),
    # Browse orchestrator (alias to autopilot)
    "browse_orchestrator": ("tools.autopilot", "AutopilotTool"),
    # Streaming demo (utility)
    "stream_demo": ("tools.stream_demo", "StreamDemoTool"),

}
# Visibility map for tools: 'core' | 'advanced' | 'hidden'
TOOL_VISIBILITY = {
    # Core verbs
    "status": "core",
    "chat": "core",
    "planner": "core",
    "thinkdeep": "core",
    "analyze": "core",
    "codereview": "core",
    "refactor": "core",
    "testgen": "core",
    "debug": "core",
    "autopilot": "core",
    # Auxiliary (advanced)
    "provider_capabilities": "advanced",
    "listmodels": "advanced",
    "activity": "advanced",
    "version": "advanced",
    "kimi_chat_with_tools": "advanced",
    "kimi_upload_and_extract": "advanced",
    "glm_agent_chat": "advanced",
    "glm_agent_get_result": "advanced",
    "glm_agent_conversation": "advanced",
    "glm_upload_file": "advanced",
    "glm_multi_file_chat": "advanced",
    "consensus": "advanced",
    "docgen": "advanced",
    "secaudit": "advanced",
    "tracer": "advanced",
    "precommit": "advanced",
    "stream_demo": "advanced",
    # Hidden/internal
    "toolcall_log_tail": "hidden",
    "health": "hidden",
    "browse_orchestrator": "hidden",
    "orchestrate_auto": "hidden",
}


DEFAULT_LEAN_TOOLS = {
    "chat",
    "analyze",
    "planner",
    "thinkdeep",
    "version",
    "listmodels",
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
            self._errors[name] = str(e)

    def build_tools(self) -> None:
        disabled = {t.strip().lower() for t in os.getenv("DISABLED_TOOLS", "").split(",") if t.strip()}
        lean_mode = os.getenv("LEAN_MODE", "false").strip().lower() == "true"
        if lean_mode:
            lean_overrides = {t.strip().lower() for t in os.getenv("LEAN_TOOLS", "").split(",") if t.strip()}
            active = lean_overrides or set(DEFAULT_LEAN_TOOLS)
        else:
            active = set(TOOL_MAP.keys())

        # Ensure utilities are always on unless STRICT_LEAN is enabled
        if os.getenv("STRICT_LEAN", "false").strip().lower() != "true":
            active.update({"version", "listmodels"})

        # Remove disabled
        active = {t for t in active if t not in disabled}

        # Hide diagnostics-only tools unless explicitly enabled
        if os.getenv("DIAGNOSTICS", "false").strip().lower() != "true":
            active.discard("self-check")

        # Web tools removed; no gating needed
        for name in sorted(active):
            self._load_tool(name)

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
        """Return machine-readable descriptors for all loaded tools (MVP)."""
        descs: Dict[str, Any] = {}
        for name, tool in self._tools.items():
            try:
                # Each tool provides a default get_descriptor()
                descs[name] = tool.get_descriptor()
            except Exception as e:
                descs[name] = {"error": f"Failed to get descriptor: {e}"}
        return descs

