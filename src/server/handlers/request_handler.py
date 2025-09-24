import sys
sys.path.append(".")
from tools import TOOLS
from utils.conversation_memory import ConversationMemory
from utils.progress import emit_progress
from src.server.context import reconstruct_thread_context
from src.server.utils import parse_model_option, get_follow_up_instructions

"""
Request Handler Module

This module contains the main request handler for MCP tool calls.
It processes incoming tool execution requests and routes them to appropriate handlers.
"""

import logging
import uuid as _uuid
from typing import Any, List, Dict
from mcp.types import TextContent

logger = logging.getLogger(__name__)

async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    # Ensure providers are configured when server is used as a module (tests/audits)
    try:
        _ensure_providers_configured()
    except Exception:
        pass
    import uuid as _uuid
    req_id = str(_uuid.uuid4())
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
                mcp_logger.info(f"TOOL_CANCELLED: {name} req_id={req_id}")
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
                if name == "kimi_multi_file_chat":
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
                    return await _execute_with_monitor(lambda: tool.execute(arguments))
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
        if name == "kimi_multi_file_chat":
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
            result = await _execute_with_monitor(lambda: tool.execute(arguments))
        else:
            result = await _execute_with_monitor(lambda: tool.execute(arguments))
        # Normalize result shape to list[TextContent]
        from mcp.types import TextContent as _TextContent
        if isinstance(result, _TextContent):
            result = [result]
        elif not isinstance(result, list):
            # best-effort fallback
            try:
                result = [_TextContent(type="text", text=str(result))]
            except Exception:
                result = []

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
                    __mcp_summary_line = (
                        f"MCP_CALL_SUMMARY: tool={name} status={__status_label} step={__step_no}/{__total_steps or '?'} "
                        f"dur={__total_dur:.1f}s model={__model_used} tokens~={__tokens} cont_id={__cid or '-'} expert={__expert_status} req_id={req_id}"
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



