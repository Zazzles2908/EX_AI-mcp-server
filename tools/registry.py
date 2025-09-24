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
import logging
logger = logging.getLogger(__name__)

# Map tool names to import paths (module, class)
TOOL_MAP: Dict[str, tuple[str, str]] = {
    # Core
    "chat": ("tools.chat", "ChatTool"),
    "analyze": ("tools.workflows.analyze", "AnalyzeTool"),
    "debug": ("tools.workflows.debug", "DebugIssueTool"),
    "codereview": ("tools.workflows.codereview", "CodeReviewTool"),
    "refactor": ("tools.workflows.refactor", "RefactorTool"),
    "secaudit": ("tools.workflows.secaudit", "SecauditTool"),
    "planner": ("tools.workflows.planner", "PlannerTool"),
    "tracer": ("tools.workflows.tracer", "TracerTool"),
    "testgen": ("tools.workflows.testgen", "TestGenTool"),
    "consensus": ("tools.workflows.consensus", "ConsensusTool"),
    "thinkdeep": ("tools.workflows.thinkdeep", "ThinkDeepTool"),
    "docgen": ("tools.workflows.docgen", "DocgenTool"),
    # Utilities (always on)
    "version": ("tools.capabilities.version", "VersionTool"),
    "listmodels": ("tools.capabilities.listmodels", "ListModelsTool"),
    "self-check": ("tools.selfcheck", "SelfCheckTool"),
    # Web tools removed: internet access disabled in production build

    # Precommit and Challenge utilities
    "precommit": ("tools.workflows.precommit", "PrecommitTool"),
    "challenge": ("tools.challenge", "ChallengeTool"),
    # Orchestrators (aliases map to autopilot)
    "orchestrate_auto": ("tools.orchestrators.autopilot", "AutopilotTool"),
    # Kimi utilities
    "kimi_upload_and_extract": ("tools.providers.kimi.kimi_upload", "KimiUploadAndExtractTool"),
    "kimi_multi_file_chat": ("tools.providers.kimi.kimi_upload", "KimiMultiFileChatTool"),
    # GLM utilities
    "glm_upload_file": ("tools.providers.glm.glm_files", "GLMUploadFileTool"),
    "glm_multi_file_chat": ("tools.providers.glm.glm_files", "GLMMultiFileChatTool"),
    # GLM Agent APIs
    "glm_agent_chat": ("tools.providers.glm.glm_agents", "GLMAgentChatTool"),
    "glm_agent_get_result": ("tools.providers.glm.glm_agents", "GLMAgentGetResultTool"),
    "glm_agent_conversation": ("tools.providers.glm.glm_agents", "GLMAgentConversationTool"),
    # Kimi chat with tools/tool_choice
    "kimi_chat_with_tools": ("tools.providers.kimi.kimi_tools_chat", "KimiChatWithToolsTool"),
    # Diagnostics
    "provider_capabilities": ("tools.capabilities.provider_capabilities", "ProviderCapabilitiesTool"),
    # Observability helpers
    "toolcall_log_tail": ("tools.diagnostics.toolcall_log_tail", "ToolcallLogTail"),
    "activity": ("tools.activity", "ActivityTool"),
    # Health
    "health": ("tools.diagnostics.health", "HealthTool"),
    # Status alias (friendly summary)
    "status": ("tools.diagnostics.status", "StatusTool"),
    # Autopilot orchestrator (opt-in)
    "autopilot": ("tools.orchestrators.autopilot", "AutopilotTool"),
    # Browse orchestrator (alias to autopilot)
    "browse_orchestrator": ("tools.orchestrators.autopilot", "AutopilotTool"),
    # Streaming demo (utility)
    "stream_demo": ("tools.streaming.stream_demo", "StreamDemoTool"),

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
    "provider_capabilities": "hidden",  # AI-manager-only diagnostics
    "listmodels": "hidden",              # AI-manager-only diagnostics
    "activity": "advanced",
    "version": "hidden",                 # AI-manager-only diagnostics
    "kimi_chat_with_tools": "advanced",
    "kimi_upload_and_extract": "hidden", # backend pathway only
    "glm_agent_chat": "advanced",
    "glm_agent_get_result": "advanced",
    "glm_agent_conversation": "advanced",
    "glm_upload_file": "hidden",         # backend pathway only
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

        # Tools consolidation gating (core set / allowlist)
        tools_core_only = os.getenv("TOOLS_CORE_ONLY", "false").strip().lower() == "true"
        allowlist = {t.strip().lower() for t in os.getenv("TOOLS_ALLOWLIST", "").split(",") if t.strip()}
        CORE_SET = {
            "chat", "analyze", "codereview", "debug", "precommit", "refactor",
            "secaudit", "testgen", "thinkdeep", "tracer", "activity", "health",
            "version", "listmodels",
        }
        # Apply allowlist only for tools known in TOOL_MAP; optional extras (e.g., smart_chat)
        # are handled separately below to avoid KeyErrors during _load_tool.
        allowlist_filtered = {t for t in allowlist if t in TOOL_MAP}
        if tools_core_only:
            active = (active & CORE_SET) | allowlist_filtered
        elif allowlist_filtered:
            active = active & allowlist_filtered
        logger.info(
            f"Registry gating: core_only={tools_core_only} allowlist={sorted(list(allowlist))} final_active={sorted(list(active))}"
        )

        # Web tools removed; no gating needed
        for name in sorted(active):
            self._load_tool(name)

        # Optional: Register SmartChat via registry only when explicitly allowlisted
        try:
            enable_smart = os.getenv("ENABLE_SMART_CHAT", "false").strip().lower() in {"1", "true", "yes", "on"}
            tools_core_only = os.getenv("TOOLS_CORE_ONLY", "false").strip().lower() == "true"
            allowlist = {t.strip().lower() for t in os.getenv("TOOLS_ALLOWLIST", "").split(",") if t.strip()}

            def _is_allowed(name: str) -> bool:
                if tools_core_only:
                    return name in allowlist
                if allowlist:
                    return name in allowlist
                return True

            if enable_smart and _is_allowed("smart_chat"):
                try:
                    from tools.smart.smart_chat import SmartChatTool  # type: ignore
                    self._tools["smart_chat"] = SmartChatTool()
                    logger.info("SmartChat tool registered via registry (advisory-only; allowlist)")
                except Exception as e:
                    self._errors["smart_chat"] = str(e)
        except Exception:
            # Do not fail registry build on optional SmartChat
            pass

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

