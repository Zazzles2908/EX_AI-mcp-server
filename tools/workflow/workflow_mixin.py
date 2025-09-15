"""
Workflow Mixin for Zen MCP Tools

This module provides a sophisticated workflow-based pattern that enables tools to
perform multi-step work with structured findings and expert analysis.

Key Components:
- BaseWorkflowMixin: Abstract base class providing comprehensive workflow functionality

The workflow pattern enables tools like debug, precommit, and codereview to perform
systematic multi-step work with pause/resume capabilities, context-aware file embedding,
and seamless integration with external AI models for expert analysis.

Features:
- Multi-step workflow orchestration with pause/resume
- Context-aware file embedding optimization
- Expert analysis integration with token budgeting
- Conversation memory and threading support
- Proper inheritance-based architecture (no hasattr/getattr)
- Comprehensive type annotations for IDE support
"""

import json
import logging
import os
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from mcp.types import TextContent
from utils.progress import send_progress

from config import MCP_PROMPT_SIZE_LIMIT
from utils.conversation_memory import add_turn, create_thread

from ..shared.base_models import ConsolidatedFindings

logger = logging.getLogger(__name__)


class BaseWorkflowMixin(ABC):
    """
    Abstract base class providing guided workflow functionality for tools.

    This class implements a sophisticated workflow pattern where Claude performs
    systematic local work before calling external models for expert analysis.
    Tools can inherit from this class to gain comprehensive workflow capabilities.

    Architecture:
    - Uses proper inheritance patterns instead of hasattr/getattr
    - Provides hook methods with default implementations
    - Requires abstract methods to be implemented by subclasses
    - Fully type-annotated for excellent IDE support

    Context-Aware File Embedding:
    - Intermediate steps: Only reference file names (saves Claude's context)
    - Final steps: Embed full file content for expert analysis
    - Integrates with existing token budgeting infrastructure

    Requirements:
    This class expects to be used with BaseTool and requires implementation of:
    - get_model_provider(model_name)
    - _resolve_model_context(arguments, request)
    - get_system_prompt()
    - get_default_temperature()
    - _prepare_file_content_for_prompt()
    """

    def __init__(self) -> None:
        super().__init__()
        self.work_history: list[dict[str, Any]] = []
        self.consolidated_findings: ConsolidatedFindings = ConsolidatedFindings()
        self.initial_request: Optional[str] = None

    # ================================================================================
    # Abstract Methods - Required Implementation by BaseTool or Subclasses
    # ================================================================================

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_workflow_request_model(self) -> type:
        """Return the request model class for this workflow tool."""
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_language_instruction(self) -> str:
        """Return the language instruction for localization. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_default_temperature(self) -> float:
        """Return the default temperature for this tool. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def get_model_provider(self, model_name: str) -> Any:
        """Get model provider for the given model. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def _resolve_model_context(self, arguments: dict[str, Any], request: Any) -> tuple[str, Any]:
        """Resolve model context from arguments. Usually provided by BaseTool."""
        pass

    @abstractmethod
    def _prepare_file_content_for_prompt(
        self,
        request_files: list[str],
        continuation_id: Optional[str],
        context_description: str = "New files",
        max_tokens: Optional[int] = None,
        reserve_tokens: int = 1_000,
        remaining_budget: Optional[int] = None,
        arguments: Optional[dict[str, Any]] = None,
        model_context: Optional[Any] = None,
    ) -> tuple[str, list[str]]:
        """Prepare file content for prompts. Usually provided by BaseTool."""
        pass

    # ================================================================================
    # Abstract Methods - Tool-Specific Implementation Required
    # ================================================================================

    @abstractmethod
    def get_work_steps(self, request: Any) -> list[str]:
        """Define tool-specific work steps and criteria"""
        pass

    @abstractmethod
    def get_required_actions(self, step_number: int, confidence: str, findings: str, total_steps: int) -> list[str]:
        """Define required actions for each work phase.

        Args:
            step_number: Current step (1-based)
            confidence: Current confidence level (exploring, low, medium, high, certain)
            findings: Current findings text
            total_steps: Total estimated steps for this work

        Returns:
            List of specific actions Claude should take before calling tool again
        """
        pass

    # ================================================================================
    # Hook Methods - Default Implementations with Override Capability
    # ================================================================================

    def should_call_expert_analysis(self, consolidated_findings: ConsolidatedFindings, request=None) -> bool:
        """
        Decide when to call external model based on tool-specific criteria.

        Default implementation for tools that don't use expert analysis.
        Override this for tools that do use expert analysis.

        Args:
            consolidated_findings: Findings from workflow steps
            request: Current request object (optional for backwards compatibility)
        """
        if not self.requires_expert_analysis():
            return False

        # Check if user requested to skip assistant model
        if request and not self.get_request_use_assistant_model(request):
            return False

        # Default logic for tools that support expert analysis
        return (
            len(consolidated_findings.relevant_files) > 0
            or len(consolidated_findings.findings) >= 2
            or len(consolidated_findings.issues_found) > 0
        )

    def prepare_expert_analysis_context(self, consolidated_findings: ConsolidatedFindings) -> str:
        """
        Prepare context for external model call.

        Default implementation for tools that don't use expert analysis.
        Override this for tools that do use expert analysis.
        """
        if not self.requires_expert_analysis():
            return ""

        # Default context preparation
        context_parts = [
            f"=== {self.get_name().upper()} WORK SUMMARY ===",
            f"Total steps: {len(consolidated_findings.findings)}",
            f"Files examined: {len(consolidated_findings.files_checked)}",
            f"Relevant files: {len(consolidated_findings.relevant_files)}",
            "",
            "=== WORK PROGRESSION ===",
        ]

        for finding in consolidated_findings.findings:
            context_parts.append(finding)

        # If we have embedded file content in this workflow, include a machine-readable payload
        try:
            embedded = self.get_embedded_file_content()
            files = self.get_actually_processed_files()
        except Exception:
            embedded, files = "", []

        if embedded:
            try:
                import os as _os, json as _json
                file_items = []
                for f in files or []:
                    file_items.append({
                        "path": _os.path.basename(f),
                        "full_path": f,
                    })
                payload = {
                    "files_in_payload": file_items,
                    "combined_embedded_content": embedded,
                }
                context_parts.append("\n=== EMBEDDED FILE PAYLOAD (JSON) ===\n" + _json.dumps(payload, ensure_ascii=False) + "\n=== END EMBEDDED FILE PAYLOAD ===")
            except Exception:
                # Best-effort only; proceed without JSON payload
                context_parts.append("\n[NOTE] Embedded file content present but could not serialize JSON payload.")

        return "\n".join(context_parts)

    def requires_expert_analysis(self) -> bool:
        """
        Override this to completely disable expert analysis for the tool.

        Returns True if the tool supports expert analysis (default).
        Returns False if the tool is self-contained (like planner).
        """
        return True

    def should_include_files_in_expert_prompt(self) -> bool:
        """
        Whether to include file content in the expert analysis prompt.
        Override this to return True if your tool needs files in the prompt.
        """
        return False

    def should_embed_system_prompt(self) -> bool:
        """
        Whether to embed the system prompt in the main prompt.
        Override this to return True if your tool needs the system prompt embedded.
        """
        return False

    def get_expert_thinking_mode(self) -> str:
        """
        Get the thinking mode for expert analysis.
        Override this to customize the thinking mode.
        """
        return "high"

    def get_expert_timeout_secs(self, request=None) -> float:
        """Return wall-clock timeout for expert analysis.
        Default from env EXPERT_ANALYSIS_TIMEOUT_SECS (seconds), fallback 300.
        Tools may override (e.g., thinkdeep) for per-tool tuning.
        """
        import os
        try:
            return float(os.getenv("EXPERT_ANALYSIS_TIMEOUT_SECS", "300"))
        except Exception:
            return 300.0

    def get_expert_heartbeat_interval_secs(self, request=None) -> float:
        """Interval in seconds for emitting progress while waiting on expert analysis.
        Default from env EXPERT_HEARTBEAT_INTERVAL_SECS (seconds), fallback 10.
        """
        import os
        try:
            return float(os.getenv("EXPERT_HEARTBEAT_INTERVAL_SECS", "10"))
        except Exception:
            return 10.0

    def get_expert_time_budget_secs(self, request=None) -> float:
        """Wall-clock time budget for expert analysis before timing out or falling back.
        Defaults to 60s to keep UX under a minute.
        """
        import os
        try:
            return float(os.getenv("EXPERT_TIME_BUDGET_SECS", "60"))
        except Exception:
            return 60.0

    def get_expert_fallback_after_secs(self, request=None) -> float:
        """When to start provider fallback within the time budget.
        Defaults to 25s so we still have headroom to complete under 60s.
        """
        import os
        try:
            return float(os.getenv("EXPERT_FALLBACK_AFTER_SECS", "25"))
        except Exception:
            return 25.0

    def is_expert_fallback_enabled(self) -> bool:
        import os
        try:
            return os.getenv("EXPERT_FALLBACK_ENABLED", "true").strip().lower() == "true"
        except Exception:
            return True

    def is_deferred_results_enabled(self) -> bool:
        """Whether to return immediately with a result handle and run expert analysis in background."""
        import os
        try:
            return os.getenv("EXPERT_DEFERRED_RESULTS", "true").strip().lower() == "true"
        except Exception:
            return True

    def get_deferred_results_ttl_secs(self) -> int:
        """TTL for stored deferred results (seconds)."""
        import os
        try:
            return int(os.getenv("DEFERRED_RESULTS_TTL_SECS", "900"))
        except Exception:
            return 900


    def get_request_temperature(self, request) -> float:
        """Get temperature from request. Override for custom temperature handling."""
        try:
            return request.temperature if request.temperature is not None else self.get_default_temperature()
        except AttributeError:
            return self.get_default_temperature()

    def get_validated_temperature(self, request, model_context: Any) -> tuple[float, list[str]]:
        """
        Get temperature from request and validate it against model constraints.

        This is a convenience method that combines temperature extraction and validation
        for workflow tools. It ensures temperature is within valid range for the model.

        Args:
            request: The request object containing temperature
            model_context: Model context object containing model info

        Returns:
            Tuple of (validated_temperature, warning_messages)
        """
        temperature = self.get_request_temperature(request)
        return self.validate_and_correct_temperature(temperature, model_context)

    def get_request_thinking_mode(self, request) -> str:
        """Get thinking mode from request. Override for custom thinking mode handling."""
        try:
            return request.thinking_mode if request.thinking_mode is not None else self.get_expert_thinking_mode()
        except AttributeError:
            return self.get_expert_thinking_mode()

    def get_request_use_websearch(self, request) -> bool:
        """Get use_websearch from request. Override for custom websearch handling."""
        try:
            return request.use_websearch if request.use_websearch is not None else True
        except AttributeError:
            return True

    def get_expert_analysis_instruction(self) -> str:
        """
        Get the instruction to append after the expert context.
        Override this to provide tool-specific instructions.
        """
        return "Please provide expert analysis based on the investigation findings."

    def get_request_use_assistant_model(self, request) -> bool:
        """
        Get use_assistant_model from request with enhanced configuration support.

        Args:
            request: Current request object

        Returns:
            True if assistant model should be used, False otherwise
        """
        # Try new configuration system first
        try:
            try:
                from config.expert_analysis import should_use_expert_analysis  # primary
            except Exception:
                from utils.expert_analysis_config import should_use_expert_analysis  # fallback shim

            # Get explicit request override
            request_override = None
            try:
                if hasattr(request, 'use_assistant_model') and request.use_assistant_model is not None:
                    request_override = request.use_assistant_model
            except AttributeError:
                pass

            # Use configuration system
            return should_use_expert_analysis(
                tool_name=self.get_name(),
                request_override=request_override
            )
        except Exception as e:
            logger.debug(f"Failed to use expert analysis config system: {e}")
            # Fallback to original logic
            pass

        # Original logic as fallback
        try:
            if request.use_assistant_model is not None:
                return request.use_assistant_model
        except AttributeError:
            pass
        # Allow environment default override to make tools fast-by-default when desired
        import os as _os
        env = (_os.getenv("DEFAULT_USE_ASSISTANT_MODEL") or "").strip().lower()
        if env in ("false", "0", "no", "off"):
            return False
        return True

    def get_step_guidance_message(self, request) -> str:
        """
        Get step guidance message. Override for tool-specific guidance.
        Default implementation uses required actions.
        """
        required_actions = self.get_required_actions(
            request.step_number, self.get_request_confidence(request), request.findings, request.total_steps
        )

        next_step_number = request.step_number + 1
        return (
            f"MANDATORY: DO NOT call the {self.get_name()} tool again immediately. "
            f"You MUST first work using appropriate tools. "
            f"REQUIRED ACTIONS before calling {self.get_name()} step {next_step_number}:\n"
            + "\n".join(f"{i + 1}. {action}" for i, action in enumerate(required_actions))
            + f"\n\nOnly call {self.get_name()} again with step_number: {next_step_number} "
            f"AFTER completing this work."
        )

    def _prepare_files_for_expert_analysis(self) -> str:
        """
        Prepare file content for expert analysis.

        EXPERT ANALYSIS REQUIRES ACTUAL FILE CONTENT:
        Expert analysis needs actual file content of all unique files marked as relevant
        throughout the workflow, regardless of conversation history optimization.

        SIMPLIFIED LOGIC:
        Expert analysis gets all unique files from relevant_files across the entire workflow.
        This includes:
        - Current step's relevant_files (consolidated_findings.relevant_files)
        - Plus any additional relevant_files from conversation history (if continued workflow)

        This ensures expert analysis has complete context without including irrelevant files.
        """
        all_relevant_files = set()

        # 1. Get files from current consolidated relevant_files
        all_relevant_files.update(self.consolidated_findings.relevant_files)

        # 2. Optionally get additional relevant_files from conversation history
        try:
            import os as _os
            include_history = (_os.getenv("EXPERT_INCLUDE_HISTORY", "false").strip().lower() == "true")
            if include_history:
                current_arguments = self.get_current_arguments()
                if current_arguments:
                    continuation_id = current_arguments.get("continuation_id")

                    if continuation_id:
                        from utils.conversation_memory import get_conversation_file_list, get_thread

                        thread_context = get_thread(continuation_id)
                        if thread_context:
                            # Get all files from conversation (these were relevant_files in previous steps)
                            conversation_files = get_conversation_file_list(thread_context)
                            all_relevant_files.update(conversation_files)
                            logger.debug(
                                f"[WORKFLOW_FILES] {self.get_name()}: Added {len(conversation_files)} files from conversation history"
                            )
            else:
                logger.debug("[WORKFLOW_FILES] Skipping conversation history files (EXPERT_INCLUDE_HISTORY=false)")
        except Exception as e:
            logger.warning(f"[WORKFLOW_FILES] {self.get_name()}: Could not get conversation files: {e}")

        # Convert to list and remove any empty/None values
        files_for_expert = [f for f in all_relevant_files if f and f.strip()]

        if not files_for_expert:
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: No relevant files found for expert analysis")
            return ""

        # Expert analysis needs actual file content, bypassing conversation optimization
        try:
            file_content, processed_files = self._force_embed_files_for_expert_analysis(files_for_expert)

            # Apply Advanced Context Manager optimization for expert analysis
            if file_content and len(file_content) > 15000:  # Higher threshold for expert analysis
                try:
                    from utils.advanced_context import optimize_file_content

                    optimized_content, optimization_metadata = optimize_file_content(
                        file_content=file_content,
                        file_paths=list(files_for_expert),
                        model_context=getattr(self, "_model_context", None),
                        context_label="Expert analysis files"
                    )

                    if optimization_metadata.get("optimized", False):
                        file_content = optimized_content
                        logger.info(
                            f"[CONTEXT_OPTIMIZATION] {self.get_name()}: Optimized expert analysis content "
                            f"({optimization_metadata.get('compression_ratio', 1.0):.2f} compression ratio, "
                            f"{len(optimization_metadata.get('strategies_applied', []))} strategies applied)"
                        )
                except Exception as e:
                    logger.warning(f"[CONTEXT_OPTIMIZATION] {self.get_name()}: Failed to optimize expert analysis content: {e}")
                    # Continue with original content if optimization fails

            # Update consolidated findings with the actual files processed so files_examined is accurate
            if processed_files:
                self.consolidated_findings.files_checked.update(processed_files)
                logger.debug(
                    f"[WORKFLOW_FILES] {self.get_name()}: Updated files_checked with {len(processed_files)} processed files"
                )

            logger.info(
                f"[WORKFLOW_FILES] {self.get_name()}: Prepared {len(processed_files)} unique relevant files for expert analysis "
                f"(from {len(self.consolidated_findings.relevant_files)} current relevant files)"
            )

            return file_content

        except Exception as e:
            logger.error(f"[WORKFLOW_FILES] {self.get_name()}: Failed to prepare files for expert analysis: {e}")
            return ""

    def _force_embed_files_for_expert_analysis(self, files: list[str]) -> tuple[str, list[str]]:
        """
        Force embed files for expert analysis, bypassing conversation history filtering.

        Expert analysis has different requirements than normal workflow steps:
        - Normal steps: Optimize tokens by skipping files in conversation history
        - Expert analysis: Needs actual file content regardless of conversation history

        Args:
            files: List of file paths to embed

        Returns:
            tuple[str, list[str]]: (file_content, processed_files)
        """
        from utils.file_utils import expand_paths, read_files
        import os as _os

        # Prioritize current request's files and cap total to avoid runaway expansion
        try:
            args = self.get_current_arguments() or {}
            current_req_files = args.get("relevant_files") or []
        except Exception:
            current_req_files = []

        # Expand any directories first to avoid runaway embedding later
        try:
            expanded_current = expand_paths(current_req_files)
        except Exception:
            expanded_current = []
        try:
            expanded_all = expand_paths(files)
        except Exception:
            expanded_all = files[:]

        # Prioritize current request files, then any remaining unique files
        ordered: list[str] = []
        seen: set[str] = set()
        for f in expanded_current:
            if f and f not in seen:
                ordered.append(f)
                seen.add(f)
        for f in expanded_all:
            if f and f not in seen:
                ordered.append(f)
                seen.add(f)

        # Apply cap on number of files to embed for expert analysis
        try:
            max_files = int(_os.getenv("EXPERT_MAX_FILES", "10"))
            if max_files <= 0:
                max_files = 10
        except Exception:
            max_files = 10

        if len(ordered) > max_files:
            capped = ordered[:max_files]
            logger.info(
                f"[WORKFLOW_FILES] {self.get_name()}: Capped expert files to {len(capped)}/{len(ordered)} (EXPERT_MAX_FILES={max_files})"
            )
        else:
            capped = ordered

        # Get token budget for files
        current_model_context = self.get_current_model_context()
        if current_model_context:
            try:
                token_allocation = current_model_context.calculate_token_allocation()
                max_tokens = token_allocation.file_tokens
                logger.debug(
                    f"[WORKFLOW_FILES] {self.get_name()}: Using {max_tokens:,} tokens for expert analysis files"
                )
            except Exception as e:
                logger.warning(f"[WORKFLOW_FILES] {self.get_name()}: Failed to get token allocation: {e}")
                max_tokens = 100_000  # Fallback
        else:
            max_tokens = 100_000  # Fallback

        # Read files directly without conversation history filtering (capped and prioritized)
        logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Force embedding {len(capped)} files for expert analysis")
        file_content = read_files(
            capped,
            max_tokens=max_tokens,
            reserve_tokens=1000,
            include_line_numbers=self.wants_line_numbers_by_default(),
        )

        # Expand paths to get individual files for tracking
        processed_files = expand_paths(capped)

        logger.debug(
            f"[WORKFLOW_FILES] {self.get_name()}: Expert analysis embedding: {len(processed_files)} files, "
            f"{len(file_content):,} characters"
        )

        return file_content, processed_files

    def wants_line_numbers_by_default(self) -> bool:
        """
        Whether this tool wants line numbers in file content by default.
        Override this to customize line number behavior.
        """
        return True  # Most workflow tools benefit from line numbers for analysis

    def _add_files_to_expert_context(self, expert_context: str, file_content: str) -> str:
        """
        Add file content to the expert context.
        Override this to customize how files are added to the context.
        """
        return f"{expert_context}\n\n=== ESSENTIAL FILES ===\n{file_content}\n=== END ESSENTIAL FILES ==="

    def _optimize_cross_tool_context(self, request: Any, arguments: dict[str, Any]) -> None:
        """
        Apply cross-tool context optimization for better continuity.

        This method optimizes context when switching between tools in a conversation
        thread, ensuring important context is preserved across tool boundaries.
        """
        continuation_id = self.get_request_continuation_id(request)
        if not continuation_id:
            return  # No cross-tool context for new conversations

        try:
            from utils.conversation_memory import get_thread
            from utils.advanced_context import optimize_cross_tool_context

            thread_context = get_thread(continuation_id)
            if not thread_context or not thread_context.turns:
                return  # No conversation history to optimize

            # Determine previous tool from conversation history
            previous_tool = None
            current_tool = self.get_name()

            # Find the most recent assistant turn to identify previous tool
            for turn in reversed(thread_context.turns):
                if turn.role == "assistant" and turn.tool_name and turn.tool_name != current_tool:
                    previous_tool = turn.tool_name
                    break

            if not previous_tool:
                return  # No previous tool found or same tool continuation

            # Apply cross-tool context optimization
            model_context = getattr(self, "_model_context", None)
            if model_context:
                optimized_context, metadata = optimize_cross_tool_context(
                    current_tool=current_tool,
                    previous_tool=previous_tool,
                    thread_context=thread_context,
                    model_context=model_context,
                    preserve_tool_transitions=True
                )

                if metadata.get("optimized", False):
                    # Store optimized context for use in expert analysis
                    self._cross_tool_context = optimized_context
                    logger.info(
                        f"[CONTEXT_OPTIMIZATION] {current_tool}: Cross-tool context optimized "
                        f"({previous_tool} → {current_tool}, "
                        f"{metadata.get('compression_ratio', 1.0):.2f} compression ratio)"
                    )
                else:
                    self._cross_tool_context = None

        except Exception as e:
            logger.warning(f"[CONTEXT_OPTIMIZATION] {self.get_name()}: Failed to optimize cross-tool context: {e}")
            self._cross_tool_context = None

    # ================================================================================
    # Context-Aware File Embedding - Core Implementation
    # ================================================================================

    def _handle_workflow_file_context(self, request: Any, arguments: dict[str, Any]) -> None:
        # Centralized secure path normalization for relevant_files when enforced
        try:
            from config import SECURE_INPUTS_ENFORCED as _SEC_ENF
            if _SEC_ENF:
                try:
                    from src.core.validation.secure_input_validator import SecureInputValidator as _SIV
                    _v = _SIV()
                    try:
                        _files = self.get_request_relevant_files(request) or []
                    except Exception:
                        _files = []
                    if _files:
                        _norm = []
                        for _f in _files:
                            try:
                                _p = _v.normalize_and_check(_f)
                                _norm.append(str(_p))
                            except Exception as _e:
                                logger.warning(f"[WORKFLOW_FILES] {self.get_name()}: secure normalization failed for {_f}: {_e}")
                        if _norm:
                            try:
                                request.relevant_files = _norm
                            except Exception:
                                pass
                except Exception:
                    # If validator import fails, continue with existing behavior
                    pass
        except Exception:
            pass

        """
        Handle file context appropriately based on workflow phase.

        CONTEXT-AWARE FILE EMBEDDING STRATEGY:
        1. Intermediate steps + continuation: Only reference file names (save Claude's context)
        2. Final step: Embed full file content for expert analysis
        3. Expert analysis: Always embed relevant files with token budgeting

        This prevents wasting Claude's limited context on intermediate steps while ensuring
        the final expert analysis has complete file context.
        """
        continuation_id = self.get_request_continuation_id(request)
        is_final_step = not self.get_request_next_step_required(request)
        step_number = self.get_request_step_number(request)

        # Extract model context for token budgeting
        model_context = arguments.get("_model_context")
        self._model_context = model_context

        # Clear any previous file context to ensure clean state
        self._embedded_file_content = ""
        self._file_reference_note = ""
        self._actually_processed_files = []

        # Determine if we should embed files or just reference them
        should_embed_files = self._should_embed_files_in_workflow_step(step_number, continuation_id, is_final_step)

        if should_embed_files:
            # Final step or expert analysis - embed full file content
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Embedding files for final step/expert analysis")
            # If chunked reader is enabled, prefer chunked embedding to avoid budget overflows
            import os as _os
            if _os.getenv("CHUNKED_READER_ENABLED", "false").strip().lower() == "true":
                try:
                    request_files = self.get_request_relevant_files(request)
                    if request_files:
                        from utils.file_chunker import chunked_read
                        chunk = chunked_read(request_files)
                        if chunk:
                            # Store as embedded content directly; mark processed files as the requested set
                            self._embedded_file_content = chunk
                            self._actually_processed_files = request_files
                            logger.info(f"[WORKFLOW_FILES] {self.get_name()}: Used CHUNKED reader for final step")
                        else:
                            self._embed_workflow_files(request, arguments)
                    else:
                        self._embed_workflow_files(request, arguments)
                except Exception as _e:
                    logger.warning(f"[WORKFLOW_FILES] {self.get_name()}: chunked reader failed, falling back: {_e}")
                    self._embed_workflow_files(request, arguments)
            else:
                self._embed_workflow_files(request, arguments)
        else:
            # Intermediate step with continuation - only reference file names
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Only referencing file names for intermediate step")
            self._reference_workflow_files(request)

    def _should_embed_files_in_workflow_step(
        self, step_number: int, continuation_id: Optional[str], is_final_step: bool
    ) -> bool:
        """
        Determine whether to embed file content based on workflow context.

        CORRECT LOGIC:
        - NEVER embed files when Claude is getting the next step (next_step_required=True)
        - ONLY embed files when sending to external model (next_step_required=False)

        Args:
            step_number: Current step number
            continuation_id: Thread continuation ID (None for new conversations)
            is_final_step: Whether this is the final step (next_step_required == False)

        Returns:
            bool: True if files should be embedded, False if only referenced
        """
        # RULE 1: Final steps (no more steps needed) - embed files for expert analysis
        if is_final_step:
            logger.debug("[WORKFLOW_FILES] Final step - will embed files for expert analysis")
            return True

        # RULE 2: Any intermediate step (more steps needed) - NEVER embed files
        # This includes:
        # - New conversations with next_step_required=True
        # - Steps with continuation_id and next_step_required=True
        logger.debug("[WORKFLOW_FILES] Intermediate step (more work needed) - will only reference files")
        return False

    def _embed_workflow_files(self, request: Any, arguments: dict[str, Any]) -> None:
        """
        Embed full file content for final steps and expert analysis.
        Uses proper token budgeting like existing debug.py.
        """
        # Use relevant_files as the standard field for workflow tools
        request_files = self.get_request_relevant_files(request)
        if not request_files:
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: No relevant_files to embed")
            return

        try:
            # Model context should be available from early validation, but might be deferred for tests
            current_model_context = self.get_current_model_context()
            if not current_model_context:
                # Try to resolve model context now (deferred from early validation)
                try:
                    model_name, model_context = self._resolve_model_context(arguments, request)
                    self._model_context = model_context
                    self._current_model_name = model_name
                except Exception as e:
                    logger.error(f"[WORKFLOW_FILES] {self.get_name()}: Failed to resolve model context: {e}")
                    # Create fallback model context (preserves existing test behavior)
                    from utils.model_context import ModelContext

                    model_name = self.get_request_model_name(request)
                    self._model_context = ModelContext(model_name)
                    self._current_model_name = model_name

            # Use the same file preparation logic as BaseTool with token budgeting
            continuation_id = self.get_request_continuation_id(request)
            remaining_tokens = arguments.get("_remaining_tokens")

            file_content, processed_files = self._prepare_file_content_for_prompt(
                request_files,
                continuation_id,
                "Workflow files for analysis",
                remaining_budget=remaining_tokens,
                arguments=arguments,
                model_context=self._model_context,
            )

            # Apply Advanced Context Manager optimization for large content
            if file_content and len(file_content) > 10000:  # Only optimize substantial content
                try:
                    from utils.advanced_context import optimize_file_content

                    optimized_content, optimization_metadata = optimize_file_content(
                        file_content=file_content,
                        file_paths=request_files,
                        model_context=self._model_context,
                        context_label="Workflow files for analysis"
                    )

                    if optimization_metadata.get("optimized", False):
                        file_content = optimized_content
                        logger.info(
                            f"[CONTEXT_OPTIMIZATION] {self.get_name()}: Optimized file content "
                            f"({optimization_metadata.get('compression_ratio', 1.0):.2f} compression ratio, "
                            f"{len(optimization_metadata.get('strategies_applied', []))} strategies applied)"
                        )
                except Exception as e:
                    logger.warning(f"[CONTEXT_OPTIMIZATION] {self.get_name()}: Failed to optimize file content: {e}")
                    # Continue with original content if optimization fails

            # Store for use in expert analysis
            self._embedded_file_content = file_content
            self._actually_processed_files = processed_files

            # Update consolidated findings with the actual files processed so files_examined is accurate
            try:
                self.consolidated_findings.files_checked.update(processed_files)
            except Exception:
                pass

            logger.info(
                f"[WORKFLOW_FILES] {self.get_name()}: Embedded {len(processed_files)} relevant_files for final analysis"
            )
            # If token budget forced truncation, add a concise summary of remaining files
            try:
                from utils.file_utils import expand_paths
                requested = set(expand_paths(request_files))
                embedded = set(processed_files or [])
                remaining = [f for f in requested if f not in embedded]
                if remaining:
                    logger.info(
                        f"[WORKFLOW_FILES] {self.get_name()}: Token budget excluded {len(remaining)} files; appending summary note"
                    )
                    names = [os.path.basename(f) for f in list(remaining)[:20]]
                    note = "\n\n--- NOTE: Additional files not embedded due to token budget ---\n" \
                           + "\n".join(f"  - {n}" for n in names) \
                           + ("\n  - ... (more)" if len(remaining) > 20 else "") \
                           + "\n--- END NOTE ---\n"
                    self._embedded_file_content = (self._embedded_file_content or "") + note
            except Exception:
                pass


        except Exception as e:
            logger.error(f"[WORKFLOW_FILES] {self.get_name()}: Failed to embed files: {e}")
            # Continue without file embedding rather than failing
            self._embedded_file_content = ""
            self._actually_processed_files = []

    def _reference_workflow_files(self, request: Any) -> None:
        """
        Reference file names without embedding content for intermediate steps.
        Saves Claude's context while still providing file awareness.
        """
        # Workflow tools use relevant_files, not files
        request_files = self.get_request_relevant_files(request)
        logger.debug(
            f"[WORKFLOW_FILES] {self.get_name()}: _reference_workflow_files called with {len(request_files)} relevant_files"
        )

        if not request_files:
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: No files to reference, skipping")
            return

        # Store file references for conversation context
        self._referenced_files = request_files

        # Create a simple reference note
        file_names = [os.path.basename(f) for f in request_files]
        reference_note = (
            f"Files referenced in this step: {', '.join(file_names)}\n"
            f"(File content available via conversation history or can be discovered by Claude)"
        )

        self._file_reference_note = reference_note
        logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Set _file_reference_note: {self._file_reference_note}")

        logger.info(
            f"[WORKFLOW_FILES] {self.get_name()}: Referenced {len(request_files)} files without embedding content"
        )

    # ================================================================================
    # Main Workflow Orchestration
    # ================================================================================

    async def execute_workflow(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Main workflow orchestration following debug tool pattern.

        Comprehensive workflow implementation that handles all common patterns:
        1. Request validation and step management
        2. Continuation and backtracking support
        3. Step data processing and consolidation
        4. Tool-specific field mapping and customization
        5. Completion logic with optional expert analysis
        6. Generic "certain confidence" handling
        7. Step guidance and required actions
        8. Conversation memory integration
        """
        from mcp.types import TextContent

        try:
            # Store arguments for access by helper methods
            self._current_arguments = arguments

            # Validate request using tool-specific model
            request = self.get_workflow_request_model()(**arguments)

            # Emit progress start breadcrumb
            try:
                send_progress(f"{self.get_name()}: Starting step {request.step_number}/{request.total_steps} - {request.step[:80] if request.step else ''}")
            except Exception:
                pass

            # Validate step field size (basic validation for workflow instructions)
            # If step is too large, user should use shorter instructions and put details in files
            step_content = request.step
            if step_content and len(step_content) > MCP_PROMPT_SIZE_LIMIT:
                from tools.models import ToolOutput

                error_output = ToolOutput(
                    status="resend_prompt",
                    content="Step instructions are too long. Please use shorter instructions and provide detailed context via file paths instead.",
                    content_type="text",
                    metadata={"prompt_size": len(step_content), "limit": MCP_PROMPT_SIZE_LIMIT},
                )
                raise ValueError(f"MCP_SIZE_CHECK:{error_output.model_dump_json()}")

            # Validate file paths for security (same as base tool)
            # Use try/except instead of hasattr as per coding standards
            try:
                path_error = self.validate_file_paths(request)
                if path_error:
                    from tools.models import ToolOutput

                    error_output = ToolOutput(
                        status="error",
                        content=path_error,
                        content_type="text",
                    )
                    return [TextContent(type="text", text=error_output.model_dump_json())]
            except AttributeError:
                # validate_file_paths method not available - skip validation
                pass

            # Try to validate model availability early for production scenarios
            # For tests, defer model validation to later to allow mocks to work
            # IMPORTANT: Only resolve model early when we actually plan to use expert analysis.
            try:
                should_resolve_model = False
                try:
                    # Resolve only if this tool uses expert analysis AND caller didn't disable it
                    if self.requires_expert_analysis() and self.get_request_use_assistant_model(request):
                        should_resolve_model = True
                except Exception:
                    # Be conservative if any check fails
                    should_resolve_model = True

                if should_resolve_model:
                    model_name, model_context = self._resolve_model_context(arguments, request)
                    # Store for later use
                    self._current_model_name = model_name
                    self._model_context = model_context
                else:
                    # Skip early model resolution for local-only flows (fewer moving parts)
                    self._current_model_name = None
                    self._model_context = None
            except ValueError as e:
                # Model resolution failed - in production this would be an error,
                # but for tests we defer to allow mocks to handle model resolution
                logger.debug(f"Early model validation failed, deferring to later: {e}")
                self._current_model_name = None
                self._model_context = None

            # Handle continuation
            continuation_id = request.continuation_id

            # Adjust total steps if needed
            if request.step_number > request.total_steps:
                request.total_steps = request.step_number

            # Create thread for first step
            if not continuation_id and request.step_number == 1:
                clean_args = {k: v for k, v in arguments.items() if k not in ["_model_context", "_resolved_model_name"]}
                continuation_id = create_thread(self.get_name(), clean_args)
                self.initial_request = request.step
                # Allow tools to store initial description for expert analysis
                self.store_initial_issue(request.step)

            # Handle backtracking if requested
            backtrack_step = self.get_backtrack_step(request)
            if backtrack_step:
                self._handle_backtracking(backtrack_step)

            # Process work step - allow tools to customize field mapping
            step_data = self.prepare_step_data(request)
            try:
                send_progress(f"{self.get_name()}: Processed step data. Updating findings...")
            except Exception:
                pass

            # Store in history
            self.work_history.append(step_data)

            # Update consolidated findings
            self._update_consolidated_findings(step_data)

            # Handle file context appropriately based on workflow phase
            self._handle_workflow_file_context(request, arguments)

            # Apply cross-tool context optimization if continuing from another tool
            self._optimize_cross_tool_context(request, arguments)

            # Build response with tool-specific customization
            response_data = self.build_base_response(request, continuation_id)

            # If work is complete, handle completion logic
            if not request.next_step_required:
                try:
                    send_progress(f"{self.get_name()}: Finalizing - calling expert analysis if required...")
                except Exception:
                    pass
                response_data = await self.handle_work_completion(response_data, request, arguments)
            else:
                # Force Claude to work before calling tool again
                response_data = self.handle_work_continuation(response_data, request)

            # Allow tools to customize the final response
            response_data = self.customize_workflow_response(response_data, request)

            # Add metadata (provider_used and model_used) to workflow response
            self._add_workflow_metadata(response_data, arguments)

            # Attach per-call progress log into metadata for UI clients
            try:
                from utils.progress import get_progress_log as _get_progress_log
                prog = _get_progress_log()
                if prog:
                    response_data.setdefault("metadata", {})["progress"] = prog
            except Exception:
                pass

            try:
                send_progress(f"{self.get_name()}: Step {request.step_number}/{request.total_steps} complete")
            except Exception:
                pass

            # Store in conversation memory
            if continuation_id:
                self.store_conversation_turn(continuation_id, response_data, request)

            return [TextContent(type="text", text=json.dumps(response_data, indent=2, ensure_ascii=False))]

        except Exception as e:
            logger.error(f"Error in {self.get_name()} work: {e}", exc_info=True)
            error_data = {
                "status": f"{self.get_name()}_failed",
                "error": str(e),
                "step_number": arguments.get("step_number", 0),
            }

            # Add metadata to error responses too
            self._add_workflow_metadata(error_data, arguments)

            return [TextContent(type="text", text=json.dumps(error_data, indent=2, ensure_ascii=False))]

    # Hook methods for tool customization

    def prepare_step_data(self, request) -> dict:
        """
        Prepare step data from request. Tools can override to customize field mapping.
        """
        # Optional security enforcement per Cleanup/Upgrade prompts
        try:
            from config import SECURE_INPUTS_ENFORCED
            if SECURE_INPUTS_ENFORCED:
                from pathlib import Path
                from src.core.validation.secure_input_validator import SecureInputValidator

                repo_root = Path(__file__).resolve().parents[2]
                v = SecureInputValidator(repo_root=str(repo_root))

                # Normalize relevant_files within repo
                try:
                    req_files = self.get_request_relevant_files(request) or []
                except Exception:
                    req_files = []
                if req_files:
                    normalized_files: list[str] = []
                    for f in req_files:
                        p = v.normalize_and_check(f)
                        normalized_files.append(str(p))
                    # Update request to the normalized list
                    try:
                        request.relevant_files = normalized_files
                    except Exception:
                        pass

                # Validate images count and normalize path-based images
                try:
                    imgs = self.get_request_images(request) or []
                except Exception:
                    imgs = []
                v.validate_images([0] * len(imgs), max_images=10)
                normalized_images: list[str] = []
                for img in imgs:
                    if isinstance(img, str) and (img.startswith("data:") or "base64," in img):
                        normalized_images.append(img)
                    else:
                        p = v.normalize_and_check(img)
                        normalized_images.append(str(p))
                try:
                    request.images = normalized_images
                except Exception:
                    pass
        except Exception as e:
            # Raise clear error for caller visibility
            raise ValueError(f"[workflow:security] {e}")

        step_data = {
            "step": request.step,
            "step_number": request.step_number,
            "findings": request.findings,
            "files_checked": self.get_request_files_checked(request),
            "relevant_files": self.get_request_relevant_files(request),
            "relevant_context": self.get_request_relevant_context(request),
            "issues_found": self.get_request_issues_found(request),
            "confidence": self.get_request_confidence(request),
            "hypothesis": self.get_request_hypothesis(request),
            "images": self.get_request_images(request),
        }
        return step_data

    def build_base_response(self, request, continuation_id: str = None) -> dict:
        """
        Build the base response structure. Tools can override for custom response fields.
        """
        response_data = {
            "status": f"{self.get_name()}_in_progress",
            "step_number": request.step_number,
            "total_steps": request.total_steps,
            "next_step_required": request.next_step_required,
            f"{self.get_name()}_status": {
                "files_checked": len(self.consolidated_findings.files_checked),
                "relevant_files": len(self.consolidated_findings.relevant_files),
                "relevant_context": len(self.consolidated_findings.relevant_context),
                "issues_found": len(self.consolidated_findings.issues_found),
                "images_collected": len(self.consolidated_findings.images),
                "current_confidence": self.get_request_confidence(request),
            },
        }
        # Optional: attach agentic routing hints without changing behavior
        try:
            from config import AGENTIC_ENGINE_ENABLED, ROUTER_ENABLED, CONTEXT_MANAGER_ENABLED
            if AGENTIC_ENGINE_ENABLED and (ROUTER_ENABLED or CONTEXT_MANAGER_ENABLED):
                from src.core.agentic.engine import AutonomousWorkflowEngine
                engine = AutonomousWorkflowEngine()
                # Build a minimal request-like structure for routing hints
                messages = []
                try:
                    # Prefer consolidated findings if available, else synthesize from request
                    initial = self.get_initial_request(request.step)
                    messages = [{"role": "user", "content": initial or (request.findings or "") }]
                except Exception:
                    pass
                decision = engine.decide({"messages": messages})
                response_data[f"{self.get_name()}_status"]["agentic_hints"] = {
                    "platform": decision.platform,
                    "estimated_tokens": decision.estimated_tokens,
                    "images_present": decision.images_present,
                    "task_type": decision.task_type,
                }
        except Exception:
            # Silently ignore hint failures; behavior must remain unchanged
            pass

        if continuation_id:
            response_data["continuation_id"] = continuation_id

        # Add file context information based on workflow phase
        embedded_content = self.get_embedded_file_content()
        reference_note = self.get_file_reference_note()
        processed_files = self.get_actually_processed_files()

        logger.debug(
            f"[WORKFLOW_FILES] {self.get_name()}: Building response - has embedded_content: {bool(embedded_content)}, has reference_note: {bool(reference_note)}"
        )

        # Prioritize embedded content over references for final steps
        if embedded_content:
            # Final step - include embedded file information
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Adding fully_embedded file context")
            response_data["file_context"] = {
                "type": "fully_embedded",
                "files_embedded": len(processed_files),
                "context_optimization": "Full file content embedded for expert analysis",
            }
        elif reference_note:
            # Intermediate step - include file reference note
            logger.debug(f"[WORKFLOW_FILES] {self.get_name()}: Adding reference_only file context")
            response_data["file_context"] = {
                "type": "reference_only",
                "note": reference_note,
                "context_optimization": "Files referenced but not embedded to preserve Claude's context window",
            }

        # Provide a standard next_call skeleton for clients and tests expecting it.
        # Only include continuation_id inside arguments when provided (omit when None).
        try:
            next_args = {
                "step": getattr(request, "step", None),
                "step_number": getattr(request, "step_number", None),
                "total_steps": getattr(request, "total_steps", None),
                "next_step_required": getattr(request, "next_step_required", None),
            }
            if continuation_id:
                next_args["continuation_id"] = continuation_id
            response_data["next_call"] = {"tool": self.get_name(), "arguments": next_args}
        except Exception:
            # Non-fatal; keep legacy behavior if request lacks attributes
            pass

        return response_data

    def should_skip_expert_analysis(self, request, consolidated_findings) -> bool:
        """
        Determine if expert analysis should be skipped due to high certainty.

        Default: False (always call expert analysis)
        Override in tools like debug to check for "certain" confidence.
        """
        return False

    def handle_completion_without_expert_analysis(self, request, consolidated_findings) -> dict:
        """
        Handle completion when skipping expert analysis.

        Tools can override this for custom high-confidence completion handling.
        Default implementation provides generic response.
        """
        work_summary = self.prepare_work_summary()
        continuation_id = self.get_request_continuation_id(request)

        response_data = {
            "status": self.get_completion_status(),
            f"complete_{self.get_name()}": {
                "initial_request": self.get_initial_request(request.step),
                "steps_taken": len(consolidated_findings.findings),
                "files_examined": list(consolidated_findings.files_checked),
                "relevant_files": list(consolidated_findings.relevant_files),
                "relevant_context": list(consolidated_findings.relevant_context),
                "work_summary": work_summary,
                "final_analysis": self.get_final_analysis_from_request(request),
                "confidence_level": self.get_confidence_level(request),
            },
            "next_steps": self.get_completion_message(),
            "skip_expert_analysis": True,
            "expert_analysis": {
                "status": self.get_skip_expert_analysis_status(),
                "reason": self.get_skip_reason(),
            },
        }

        if continuation_id:
            response_data["continuation_id"] = continuation_id

        return response_data

    # ================================================================================
    # Inheritance Hook Methods - Replace hasattr/getattr Anti-patterns
    # ================================================================================

    def get_request_confidence(self, request: Any) -> str:
        """Get confidence from request. Override for custom confidence handling."""
        try:
            return request.confidence or "low"
        except AttributeError:
            return "low"

    def get_request_relevant_context(self, request: Any) -> list[str]:
        """Get relevant context from request. Override for custom field mapping."""
        try:
            return request.relevant_context or []
        except AttributeError:
            return []

    def get_request_issues_found(self, request: Any) -> list[str]:
        """Get issues found from request. Override for custom field mapping."""
        try:
            return request.issues_found or []
        except AttributeError:
            return []

    def get_request_hypothesis(self, request: Any) -> Optional[str]:
        """Get hypothesis from request. Override for custom field mapping."""
        try:
            return request.hypothesis
        except AttributeError:
            return None

    def get_request_images(self, request: Any) -> list[str]:
        """Get images from request. Override for custom field mapping."""
        try:
            return request.images or []
        except AttributeError:
            return []

    # File Context Access Methods

    def get_embedded_file_content(self) -> str:
        """Get embedded file content. Returns empty string if not available."""
        try:
            return self._embedded_file_content or ""
        except AttributeError:
            return ""

    def get_file_reference_note(self) -> str:
        """Get file reference note. Returns empty string if not available."""
        try:
            return self._file_reference_note or ""
        except AttributeError:
            return ""

    def get_actually_processed_files(self) -> list[str]:
        """Get list of actually processed files. Returns empty list if not available."""
        try:
            return self._actually_processed_files or []
        except AttributeError:
            return []

    def get_current_model_context(self):
        """Get current model context. Returns None if not available."""
        try:
            return self._model_context
        except AttributeError:
            return None

    def get_request_model_name(self, request: Any) -> str:
        """Get model name from request. Avoid misleading defaults like 'flash'."""
        try:
            m = getattr(request, "model", None)
            if m and isinstance(m, str) and m.strip():
                return m
        except Exception:
            pass
        # Fall back to configured DEFAULT_MODEL; let callers handle 'auto' if needed
        from config import DEFAULT_MODEL
        return DEFAULT_MODEL

    def get_request_continuation_id(self, request: Any) -> Optional[str]:
        """Get continuation ID from request. Override for custom continuation handling."""
        try:
            return request.continuation_id
        except AttributeError:
            return None

    def get_request_next_step_required(self, request: Any) -> bool:
        """Get next step required from request. Override for custom step handling."""
        try:
            return request.next_step_required
        except AttributeError:
            return True

    def get_request_step_number(self, request: Any) -> int:
        """Get step number from request. Override for custom step handling."""
        try:
            return request.step_number or 1
        except AttributeError:
            return 1

    def get_request_relevant_files(self, request: Any) -> list[str]:
        """Get relevant files from request. Override for custom file handling."""
        try:
            return request.relevant_files or []
        except AttributeError:
            return []

    def get_request_files_checked(self, request: Any) -> list[str]:
        """Get files checked from request. Override for custom file handling."""
        try:
            return request.files_checked or []
        except AttributeError:
            return []

    def get_current_arguments(self) -> dict[str, Any]:
        """Get current arguments. Returns empty dict if not available."""
        try:
            return self._current_arguments or {}
        except AttributeError:
            return {}

    def get_backtrack_step(self, request) -> Optional[int]:
        """Get backtrack step from request. Override for custom backtrack handling."""
        try:
            return request.backtrack_from_step
        except AttributeError:
            return None

    def store_initial_issue(self, step_description: str):
        """Store initial issue description. Override for custom storage."""
        # Default implementation - tools can override to store differently
        self.initial_issue = step_description

    def get_initial_request(self, fallback_step: str) -> str:
        """Get initial request description. Override for custom retrieval."""
        try:
            return self.initial_request or fallback_step
        except AttributeError:
            return fallback_step

    # Default implementations for inheritance hooks

    def prepare_work_summary(self) -> str:
        """Prepare work summary. Override for custom implementation."""
        return f"Completed {len(self.consolidated_findings.findings)} work steps"

    def get_completion_status(self) -> str:
        """Get completion status. Override for tool-specific status."""
        return "high_confidence_completion"

    def get_final_analysis_from_request(self, request):
        """Extract final analysis from request. Override for tool-specific fields."""
        return self.get_request_hypothesis(request)

    def get_confidence_level(self, request) -> str:
        """Get confidence level. Override for tool-specific confidence handling."""
        return self.get_request_confidence(request) or "high"

    def get_completion_message(self) -> str:
        """Get completion message. Override for tool-specific messaging."""
        return (
            f"{self.get_name().capitalize()} complete with high confidence. Present results "
            "and proceed with implementation without requiring further consultation."
        )

    def get_skip_reason(self) -> str:
        """Get reason for skipping expert analysis. Override for tool-specific reasons."""
        return f"{self.get_name()} completed with sufficient confidence"

    def get_skip_expert_analysis_status(self) -> str:
        """Get status for skipped expert analysis. Override for tool-specific status."""
        return "skipped_by_tool_design"

    def get_completion_next_steps_message(self, expert_analysis_used: bool = False) -> str:
        """
        Get the message to show when work is complete.
        Tools can override for custom messaging.

        Args:
            expert_analysis_used: True if expert analysis was successfully executed
        """
        base_message = (
            f"{self.get_name().upper()} IS COMPLETE. You MUST now summarize and present ALL key findings, confirmed "
            "hypotheses, and exact recommended solutions. Clearly identify the most likely root cause and "
            "provide concrete, actionable implementation guidance. Highlight affected code paths and display "
            "reasoning that led to this conclusion—make it easy for a developer to understand exactly where "
            "the problem lies."
        )

        # Add expert analysis guidance only when expert analysis was actually used
        if expert_analysis_used:
            expert_guidance = self.get_expert_analysis_guidance()
            if expert_guidance:
                return f"{base_message}\n\n{expert_guidance}"

        return base_message

    def get_expert_analysis_guidance(self) -> str:
        """
        Get additional guidance for handling expert analysis results.

        Subclasses can override this to provide specific instructions about how
        to validate and use expert analysis findings. Returns empty string by default.

        When expert analysis is called, this guidance will be:
        1. Appended to the completion next steps message
        2. Added as "important_considerations" field in the response data

        Example implementation:
        ```python
        def get_expert_analysis_guidance(self) -> str:
            return (
                "IMPORTANT: Expert analysis provided above. You MUST validate "
                "the expert findings rather than accepting them blindly. "
                "Cross-reference with your own investigation and ensure "
                "recommendations align with the codebase context."
            )
        ```

        Returns:
            Additional guidance text or empty string if no guidance needed
        """
        return ""

    def customize_workflow_response(self, response_data: dict, request) -> dict:
        """
        Allow tools to customize the workflow response before returning.

        Tools can override this to add tool-specific fields, modify status names,
        customize field mapping, etc. Default implementation returns unchanged.
        """
        # Ensure file context information is preserved in all response paths
        if not response_data.get("file_context"):
            embedded_content = self.get_embedded_file_content()
            reference_note = self.get_file_reference_note()
            processed_files = self.get_actually_processed_files()

            # Prioritize embedded content over references for final steps
            if embedded_content:
                response_data["file_context"] = {
                    "type": "fully_embedded",
                    "files_embedded": len(processed_files),
                    "context_optimization": "Full file content embedded for expert analysis",
                }
            elif reference_note:
                response_data["file_context"] = {
                    "type": "reference_only",
                    "note": reference_note,
                    "context_optimization": "Files referenced but not embedded to preserve Claude's context window",
                }

        return response_data

    def store_conversation_turn(self, continuation_id: str, response_data: dict, request):
        """
        Store the conversation turn. Tools can override for custom memory storage.
        """
        # CRITICAL: Extract clean content for conversation history (exclude internal workflow metadata)
        clean_content = self._extract_clean_workflow_content_for_history(response_data)

        add_turn(
            thread_id=continuation_id,
            role="assistant",
            content=clean_content,  # Use cleaned content instead of full response_data
            tool_name=self.get_name(),
            files=self.get_request_relevant_files(request),
            images=self.get_request_images(request),
        )

    def _add_workflow_metadata(self, response_data: dict, arguments: dict[str, Any]) -> None:
        """
        Add metadata (provider_used and model_used) to workflow response.

        This ensures workflow tools have the same metadata as regular tools,
        making it consistent across all tool types for tracking which provider
        and model were used for the response.

        Args:
            response_data: The response data dictionary to modify
            arguments: The original arguments containing model context
        """
        try:
            # Get model information from arguments (set by server.py)
            resolved_model_name = arguments.get("_resolved_model_name")
            model_context = arguments.get("_model_context")

            if resolved_model_name and model_context:
                # Extract provider information from model context
                provider = model_context.provider
                provider_name = provider.get_provider_type().value if provider else "unknown"

                # Create metadata dictionary
                metadata = {
                    "tool_name": self.get_name(),
                    "model_used": resolved_model_name,
                    "provider_used": provider_name,
                }

                # Preserve existing metadata and add workflow metadata
                if "metadata" not in response_data:
                    response_data["metadata"] = {}
                response_data["metadata"].update(metadata)

                logger.debug(
                    f"[WORKFLOW_METADATA] {self.get_name()}: Added metadata - "
                    f"model: {resolved_model_name}, provider: {provider_name}"
                )
            else:
                # Fallback - try to get model info from request
                request = self.get_workflow_request_model()(**arguments)
                model_name = self.get_request_model_name(request)

                # Basic metadata without provider info
                metadata = {
                    "tool_name": self.get_name(),
                    "model_used": model_name,
                    "provider_used": "unknown",
                }

                # Preserve existing metadata and add workflow metadata
                if "metadata" not in response_data:
                    response_data["metadata"] = {}
                response_data["metadata"].update(metadata)

                logger.debug(
                    f"[WORKFLOW_METADATA] {self.get_name()}: Added fallback metadata - "
                    f"model: {model_name}, provider: unknown"
                )

        except Exception as e:
            # Don't fail the workflow if metadata addition fails
            logger.warning(f"[WORKFLOW_METADATA] {self.get_name()}: Failed to add metadata: {e}")
            # Still add basic metadata with tool name
            response_data["metadata"] = {"tool_name": self.get_name()}

    def _extract_clean_workflow_content_for_history(self, response_data: dict) -> str:
        """
        Extract clean content from workflow response suitable for conversation history.

        This method removes internal workflow metadata, continuation offers, and
        status information that should not appear when the conversation is
        reconstructed for expert models or other tools.

        Args:
            response_data: The full workflow response data

        Returns:
            str: Clean content suitable for conversation history storage
        """
        # Create a clean copy with only essential content for conversation history
        clean_data = {}

        # Include core content if present
        if "content" in response_data:
            clean_data["content"] = response_data["content"]

        # Include expert analysis if present (but clean it)
        if "expert_analysis" in response_data:
            expert_analysis = response_data["expert_analysis"]
            if isinstance(expert_analysis, dict):
                # Only include the actual analysis content, not metadata
                clean_expert = {}
                if "raw_analysis" in expert_analysis:
                    clean_expert["analysis"] = expert_analysis["raw_analysis"]
                elif "content" in expert_analysis:
                    clean_expert["analysis"] = expert_analysis["content"]
                if clean_expert:
                    clean_data["expert_analysis"] = clean_expert

        # Include findings/issues if present (core workflow output)
        if "complete_analysis" in response_data:
            complete_analysis = response_data["complete_analysis"]
            if isinstance(complete_analysis, dict):
                clean_complete = {}
                # Include essential analysis data without internal metadata
                for key in ["findings", "issues_found", "relevant_context", "insights"]:
                    if key in complete_analysis:
                        clean_complete[key] = complete_analysis[key]
                if clean_complete:
                    clean_data["analysis_summary"] = clean_complete

        # Include step information for context but remove internal workflow metadata
        if "step_number" in response_data:
            clean_data["step_info"] = {
                "step": response_data.get("step", ""),
                "step_number": response_data.get("step_number", 1),
                "total_steps": response_data.get("total_steps", 1),
            }

        # Exclude problematic fields that should never appear in conversation history:
        # - continuation_id (confuses LLMs with old IDs)
        # - status (internal workflow state)
        # - next_step_required (internal control flow)
        # - analysis_status (internal tracking)
        # - file_context (internal optimization info)
        # - required_actions (internal workflow instructions)

        return json.dumps(clean_data, indent=2, ensure_ascii=False)

    # Core workflow logic methods

    async def handle_work_completion(self, response_data: dict, request, arguments: dict) -> dict:
        """
        Handle work completion logic - expert analysis decision and response building.
        """
        response_data[f"{self.get_name()}_complete"] = True

        # Check if tool wants to skip expert analysis due to high certainty
        if self.should_skip_expert_analysis(request, self.consolidated_findings):
            # Handle completion without expert analysis
            completion_response = self.handle_completion_without_expert_analysis(request, self.consolidated_findings)
            response_data.update(completion_response)

            # Add cost summary for skipped expert analysis
            try:
                try:
                    from config.expert_analysis import get_expert_analysis_config  # primary
                except Exception:
                    from utils.expert_analysis_config import get_expert_analysis_config  # fallback
                from utils.expert_analysis_warnings import format_expert_analysis_completion

                config = get_expert_analysis_config()
                if config.should_show_cost_summary(self.get_name()):
                    completion_message = format_expert_analysis_completion(
                        "none", 0, self.get_name(), False
                    )
                    response_data["cost_summary"] = completion_message
            except Exception as e:
                logger.debug(f"Failed to generate cost completion message: {e}")
        elif self.requires_expert_analysis() and self.should_call_expert_analysis(self.consolidated_findings, request):
            # Standard expert analysis path (with optional deferred results)
            response_data["status"] = "calling_expert_analysis"

            # If deferred results are enabled, enqueue background expert call and return handle immediately
            if self.is_deferred_results_enabled():
                try:
                    import hashlib, json as _json
                    from utils.storage_backend import get_storage_backend

                    # Build a stable handle using tool name + thread id + time
                    thread_id = None
                    try:
                        from utils.conversation_memory import get_current_thread_id
                        thread_id = get_current_thread_id() or ""
                    except Exception:
                        thread_id = ""
                    start_ts = time.time()
                    seed = f"{self.get_name()}|{thread_id}|{start_ts}".encode()
                    result_handle = hashlib.sha256(seed).hexdigest()[:24]

                    # Snapshot arguments and minimal state for background task
                    snapshot = {
                        "arguments": {k: v for k, v in arguments.items() if k not in ["_model_context"]},
                        "request": self.get_workflow_request_model()(**arguments).__dict__ if hasattr(self, "get_workflow_request_model") else {},
                    }

                    # Store initial status
                    storage = get_storage_backend()
                    ttl = self.get_deferred_results_ttl_secs()
                    storage.set_with_ttl(f"deferred:{result_handle}", ttl, _json.dumps({
                        "status": "processing",
                        "tool": self.get_name(),
                        "created_at": int(start_ts),
                    }))
                    logger.info("[DEFERRED] %s started handle=%s ttl=%ss", self.get_name(), result_handle, ttl)

                    async def _run_and_store():
                        try:
                            # Capture provider name for observability
                            try:
                                prov_name = (self._model_context.provider.get_provider_type().value if getattr(self, "_model_context", None) and getattr(self._model_context, "provider", None) else "unknown")
                            except Exception:
                                prov_name = "unknown"
                            result = await self._call_expert_analysis(arguments, self.get_workflow_request_model()(**arguments))
                            elapsed = max(0, time.time() - start_ts)
                            storage.set_with_ttl(f"deferred:{result_handle}", ttl, _json.dumps({
                                "status": "complete",
                                "tool": self.get_name(),
                                "provider": prov_name,
                                "result": result,
                                "completed_at": int(time.time()),
                                "elapsed_seconds": round(elapsed, 2),
                            }))
                            logger.info("[DEFERRED] %s complete handle=%s elapsed=%.2fs provider=%s", self.get_name(), result_handle, elapsed, prov_name)
                        except Exception as _e:
                            storage.set_with_ttl(f"deferred:{result_handle}", ttl, _json.dumps({
                                "status": "error",
                                "tool": self.get_name(),
                                "provider": prov_name if 'prov_name' in locals() else "unknown",
                                "error": str(_e),
                                "completed_at": int(time.time()),
                                "elapsed_seconds": round(max(0, time.time() - start_ts), 2),
                            }))
                            logger.error("[DEFERRED] %s error handle=%s err=%s provider=%s", self.get_name(), result_handle, _e, (prov_name if 'prov_name' in locals() else 'unknown'))

                    # Kick off background task without blocking
                    try:
                        import asyncio as _asyncio
                        _asyncio.create_task(_run_and_store())
                    except Exception:
                        # If event loop context missing, run in thread
                        import threading
                        threading.Thread(target=lambda: _asyncio.run(_run_and_store()), daemon=True).start()

                    # Return immediate response with handle
                    response_data["expert_analysis"] = {
                        "status": "processing",
                        "result_handle": result_handle,
                        "note": "Use await_result tool with this handle to retrieve the final result.",
                    }
                    response_data["next_steps"] = "Polling is required: call await_result with result_handle."
                    return response_data
                except Exception as _de:
                    logger.debug(f"Deferred results path failed, falling back to blocking call: {_de}")

            # Add cost warning if enabled
            try:
                try:
                    from config.expert_analysis import get_expert_analysis_config  # primary
                except Exception:
                    from utils.expert_analysis_config import get_expert_analysis_config  # fallback
                from utils.expert_analysis_warnings import format_expert_analysis_warning

                config = get_expert_analysis_config()
                if config.should_show_warnings(self.get_name()):
                    # Estimate tokens and files for warning
                    estimated_tokens = 0
                    file_count = len(self.consolidated_findings.relevant_files) if self.consolidated_findings.relevant_files else 0

                    # Try to estimate tokens from file content
                    if hasattr(self, '_model_context') and self._model_context:
                        try:
                            allocation = self._model_context.calculate_token_allocation()
                            estimated_tokens = allocation.content_tokens
                        except Exception:
                            estimated_tokens = file_count * 1000  # Rough estimate
                    else:
                        estimated_tokens = file_count * 1000  # Rough estimate

                    model_name = getattr(self, '_current_model_name', 'unknown')
                    warning_message = format_expert_analysis_warning(
                        model_name, estimated_tokens, file_count, self.get_name()
                    )
                    response_data["cost_warning"] = warning_message
            except Exception as e:
                logger.debug(f"Failed to generate cost warning: {e}")

            # Call expert analysis
            expert_analysis = await self._call_expert_analysis(arguments, request)
            response_data["expert_analysis"] = expert_analysis

            # Handle special expert analysis statuses
            if isinstance(expert_analysis, dict) and expert_analysis.get("status") in [
                "files_required_to_continue",
                "investigation_paused",
                "refactoring_paused",
            ]:
                # Promote the special status to the main response
                special_status = expert_analysis["status"]
                response_data["status"] = special_status
                response_data["content"] = expert_analysis.get(
                    "raw_analysis", json.dumps(expert_analysis, ensure_ascii=False)
                )
                del response_data["expert_analysis"]

                # Update next steps for special status
                if special_status == "files_required_to_continue":
                    response_data["next_steps"] = "Provide the requested files and continue the analysis."
                else:
                    response_data["next_steps"] = expert_analysis.get(
                        "next_steps", "Continue based on expert analysis."
                    )
            elif isinstance(expert_analysis, dict) and expert_analysis.get("status") == "analysis_error":
                # Expert analysis failed - promote error status
                response_data["status"] = "error"
                response_data["content"] = expert_analysis.get("error", "Expert analysis failed")
                response_data["content_type"] = "text"
                del response_data["expert_analysis"]
            else:
                # Expert analysis was successfully executed - include expert guidance
                response_data["next_steps"] = self.get_completion_next_steps_message(expert_analysis_used=True)

                # Add expert analysis guidance as important considerations
                expert_guidance = self.get_expert_analysis_guidance()
                if expert_guidance:
                    response_data["important_considerations"] = expert_guidance

                # Add cost completion message
                try:
                    from config.expert_analysis import get_expert_analysis_config
                    from utils.expert_analysis_warnings import format_expert_analysis_completion

                    config = get_expert_analysis_config()
                    if config.should_show_cost_summary(self.get_name()):
                        model_name = getattr(self, '_current_model_name', 'unknown')
                        # Try to get actual token usage from expert analysis
                        actual_tokens = 0
                        if isinstance(expert_analysis, dict):
                            actual_tokens = expert_analysis.get('token_usage', 0)
                        if actual_tokens == 0:
                            # Fallback estimate
                            file_count = len(self.consolidated_findings.relevant_files) if self.consolidated_findings.relevant_files else 0
                            actual_tokens = file_count * 1000

                        completion_message = format_expert_analysis_completion(
                            model_name, actual_tokens, self.get_name(), True
                        )
                        response_data["cost_summary"] = completion_message
                except Exception as e:
                    logger.debug(f"Failed to generate cost completion message: {e}")

            # Prepare complete work summary
            work_summary = self._prepare_work_summary()
            response_data[f"complete_{self.get_name()}"] = {
                "initial_request": self.get_initial_request(request.step),
                "steps_taken": len(self.work_history),
                "files_examined": list(self.consolidated_findings.files_checked),
                "relevant_files": list(self.consolidated_findings.relevant_files),
                "relevant_context": list(self.consolidated_findings.relevant_context),
                "issues_found": self.consolidated_findings.issues_found,
                "work_summary": work_summary,
            }
        else:
            # Tool doesn't require expert analysis or local work was sufficient
            if not self.requires_expert_analysis():
                # Tool is self-contained (like planner)
                response_data["status"] = f"{self.get_name()}_complete"
                response_data["next_steps"] = (
                    f"{self.get_name().capitalize()} work complete. Present results to the user."
                )
            else:
                # Local work was sufficient for tools that support expert analysis
                response_data["status"] = "local_work_complete"
                response_data["next_steps"] = (
                    f"Local {self.get_name()} complete with sufficient confidence. Present findings "
                    "and recommendations to the user based on the work results."
                )

        return response_data

    def handle_work_continuation(self, response_data: dict, request) -> dict:
        """
        Handle work continuation - force pause and provide guidance.
        """
        response_data["status"] = f"pause_for_{self.get_name()}"
        response_data[f"{self.get_name()}_required"] = True

        # Get tool-specific required actions
        required_actions = self.get_required_actions(
            request.step_number, self.get_request_confidence(request), request.findings, request.total_steps
        )
        response_data["required_actions"] = required_actions

        # Generate step guidance
        response_data["next_steps"] = self.get_step_guidance_message(request)

        # Provide explicit auto-continue hints for orchestrators/clients
        try:
            next_step = int(request.step_number) + 1
        except Exception:
            next_step = None
        response_data["continuation_required"] = True
        response_data["continuation_available"] = True
        if next_step is not None:
            response_data["next_step_number"] = next_step
        # Include a minimal next_call skeleton clients can use directly
        try:
            cont_id = self.get_request_continuation_id(request)
        except Exception:
            cont_id = None
        response_data["next_call"] = {
            "tool": self.get_name(),
            "arguments": {
                "step": f"Continue with step {next_step} as per required actions.",
                "step_number": next_step or (request.step_number + 1),
                "total_steps": request.total_steps,
                "next_step_required": next_step is not None and next_step < (getattr(request, 'total_steps', 2) or 2),
                "findings": "Summarize new insights and evidence from the required actions.",
                **({"continuation_id": cont_id} if cont_id else {}),
            },
        }

        return response_data

    def _handle_backtracking(self, backtrack_step: int):
        """Handle backtracking to a previous step"""
        # Remove findings after the backtrack point
        self.work_history = [s for s in self.work_history if s["step_number"] < backtrack_step]
        # Reprocess consolidated findings
        self._reprocess_consolidated_findings()

    def _update_consolidated_findings(self, step_data: dict):
        """Update consolidated findings with new step data"""
        self.consolidated_findings.files_checked.update(step_data.get("files_checked", []))
        self.consolidated_findings.relevant_files.update(step_data.get("relevant_files", []))
        self.consolidated_findings.relevant_context.update(step_data.get("relevant_context", []))
        self.consolidated_findings.findings.append(f"Step {step_data['step_number']}: {step_data['findings']}")
        if step_data.get("hypothesis"):
            self.consolidated_findings.hypotheses.append(
                {
                    "step": step_data["step_number"],
                    "hypothesis": step_data["hypothesis"],
                    "confidence": step_data["confidence"],
                }
            )
        if step_data.get("issues_found"):
            self.consolidated_findings.issues_found.extend(step_data["issues_found"])
        if step_data.get("images"):
            self.consolidated_findings.images.extend(step_data["images"])
        # Update confidence to latest value from this step
        if step_data.get("confidence"):
            self.consolidated_findings.confidence = step_data["confidence"]

    def _reprocess_consolidated_findings(self):
        """Reprocess consolidated findings after backtracking"""
        self.consolidated_findings = ConsolidatedFindings()
        for step in self.work_history:
            self._update_consolidated_findings(step)

    def _prepare_work_summary(self) -> str:
        """Prepare a comprehensive summary of the work"""
        summary_parts = [
            f"=== {self.get_name().upper()} WORK SUMMARY ===",
            f"Total steps: {len(self.work_history)}",
            f"Files examined: {len(self.consolidated_findings.files_checked)}",
            f"Relevant files identified: {len(self.consolidated_findings.relevant_files)}",
            f"Methods/functions involved: {len(self.consolidated_findings.relevant_context)}",
            f"Issues found: {len(self.consolidated_findings.issues_found)}",
            "",
            "=== WORK PROGRESSION ===",
        ]

        for finding in self.consolidated_findings.findings:
            summary_parts.append(finding)

        if self.consolidated_findings.hypotheses:
            summary_parts.extend(
                [
                    "",
                    "=== HYPOTHESIS EVOLUTION ===",
                ]
            )
            for hyp in self.consolidated_findings.hypotheses:
                summary_parts.append(f"Step {hyp['step']} ({hyp['confidence']} confidence): {hyp['hypothesis']}")

        if self.consolidated_findings.issues_found:
            summary_parts.extend(
                [
                    "",
                    "=== ISSUES IDENTIFIED ===",
                ]
            )
            for issue in self.consolidated_findings.issues_found:
                severity = issue.get("severity", "unknown")
                description = issue.get("description", "No description")
                summary_parts.append(f"[{severity.upper()}] {description}")

        return "\n".join(summary_parts)

    async def _call_expert_analysis(self, arguments: dict, request) -> dict:
        """Call external model for expert analysis with watchdog and graceful degradation.

        We see occasional UI disconnects exactly after '[WORKFLOW_FILES] ... Prepared X unique relevant files' and
        before '[PROGRESS] ... Step N/M complete'. That window corresponds to this method executing the slow
        provider call. If the UI disconnects (websocket drop) or the provider stalls, we still want to finish
        and persist a best-effort result instead of leaving the tool 'stuck'.
        """
        try:
            # Model context should be resolved from early validation, but handle fallback for tests
            if not self._model_context:
                try:
                    model_name, model_context = self._resolve_model_context(arguments, request)
                    self._model_context = model_context
                    self._current_model_name = model_name
                except Exception as e:
                    logger.error(f"Failed to resolve model context for expert analysis: {e}")
                    # Use request model as fallback (preserves existing test behavior)
                    model_name = self.get_request_model_name(request)
                    from utils.model_context import ModelContext
                    model_context = ModelContext(model_name)
                    self._model_context = model_context
                    self._current_model_name = model_name
            else:
                model_name = self._current_model_name

            # Primary routing v1: allow router to pick initial model for final-step expert analysis
            try:
                from utils.model_router import ModelRouter, RoutingContext
                if ModelRouter.is_enabled():
                    ctx = RoutingContext(tool_name=self.get_name(), requested_model=model_name)
                    routed_model = ModelRouter.decide(ctx)
                    if routed_model and routed_model != model_name:
                        try:
                            from utils.model_context import ModelContext
                            self._model_context = ModelContext(routed_model)
                            self._current_model_name = routed_model
                            model_name = routed_model
                            provider = self._model_context.provider
                            prov_name = provider.get_provider_type().value if provider else "unknown"
                            logger.info(f"[ROUTER] tool={self.get_name()} primary={routed_model} prev={ctx.requested_model} provider={prov_name}")
                        except Exception as _e:
                            logger.debug(f"[ROUTER] Failed to switch to routed model '{routed_model}': {_e}")
            except Exception as _e:
                logger.debug(f"[ROUTER] Routing not applied: {_e}")

            provider = self._model_context.provider

            # Prepare expert analysis context
            expert_context = self.prepare_expert_analysis_context(self.consolidated_findings)

            # Check if tool wants to include files in prompt
            if self.should_include_files_in_expert_prompt():
                # Reuse already embedded content when available to avoid double-reading files
                file_content = self.get_embedded_file_content() or self._prepare_files_for_expert_analysis()
                if file_content:
                    expert_context = self._add_files_to_expert_context(expert_context, file_content)

            # Get system prompt for this tool with localization support
            base_system_prompt = self.get_system_prompt()
            language_instruction = self.get_language_instruction()
            system_prompt = language_instruction + base_system_prompt

            # Check if tool wants system prompt embedded in main prompt
            if self.should_embed_system_prompt():
                prompt = f"{system_prompt}\n\n{expert_context}\n\n{self.get_expert_analysis_instruction()}"
                system_prompt = ""  # Clear it since we embedded it
            else:
                prompt = expert_context

            # Validate temperature against model constraints
            validated_temperature, temp_warnings = self.get_validated_temperature(request, self._model_context)

            # Log any temperature corrections
            for warning in temp_warnings:
                logger.warning(warning)

            # Watchdog with user-centric budget: stay under time budget for UX; use larger internal timeout as safety net
            hard_deadline = time.time() + self.get_expert_timeout_secs(request)
            budget_deadline = time.time() + self.get_expert_time_budget_secs(request)
            fallback_after = self.get_expert_fallback_after_secs(request)
            fallback_started = False

            # Run provider call in a thread to allow cancellation/timeouts even if provider blocks
            loop = asyncio.get_running_loop()
            def _invoke_provider():
                return provider.generate_content(
                    prompt=prompt,
                    model_name=model_name,
                    system_prompt=system_prompt,
                    temperature=validated_temperature,
                    thinking_mode=self.get_request_thinking_mode(request),
                    use_websearch=self.get_request_use_websearch(request),
                    images=list(set(self.consolidated_findings.images)) if self.consolidated_findings.images else None,
                )
            start_time = time.time()

            task = loop.run_in_executor(None, _invoke_provider)




            # Poll until done or deadline; emit progress breadcrumbs so UI stays alive
            hb = max(5.0, self.get_expert_heartbeat_interval_secs(request))
            fb_task = None  # will hold concurrent fallback task if started

            while True:
                # Start proactive fallback if primary is slow and fallback is enabled
                try:
                    if (not fallback_started) and self.is_expert_fallback_enabled() and ((time.time() - start_time) >= fallback_after):
                        fallback_started = True
                        try:
                            # Choose a smart fallback model/provider
                            from utils.model_router import get_fallback_choice
                            primary_provider = provider.get_provider_type()
                            tool_name = self.get_name()
                            fb_provider_type, fb_model = get_fallback_choice(primary_provider, tool_name)

                            if fb_provider_type and fb_model:
                                try:
                                    from src.providers.registry import ModelProviderRegistry
                                    fb_provider = ModelProviderRegistry.get_provider(fb_provider_type)
                                except Exception:
                                    fb_provider = None

                                if fb_provider is not None:
                                    def _invoke_fb_proactive():
                                        return fb_provider.generate_content(
                                            prompt=prompt,
                                            model_name=fb_model,
                                            system_prompt=system_prompt,
                                            temperature=validated_temperature,
                                            thinking_mode=self.get_request_thinking_mode(request),
                                            use_websearch=self.get_request_use_websearch(request),
                                            images=list(set(self.consolidated_findings.images)) if self.consolidated_findings.images else None,
                                        )
                                    fb_task = loop.run_in_executor(None, _invoke_fb_proactive)
                                    try:
                                        send_progress(f"{self.get_name()}: Starting proactive fallback (provider={fb_provider.get_provider_type().value}, model={fb_model})...")
                                    except Exception:
                                        pass
                        except Exception:
                            # Fallback routing not available; continue on primary
                            pass
                except Exception:
                    pass

                # If fallback is in flight and finishes first, take its result
                if fb_task is not None and fb_task.done():
                    try:
                        model_response = fb_task.result()
                        break
                    except Exception:
                        # Ignore fallback failure; continue waiting for primary
                        pass

                if task.done():
                    try:
                        model_response = task.result()
                    except Exception as e:
                        # Provider error - attempt graceful fallback on rate limit if enabled and time remains
                        try:
                            import os as _os
                            allow_fb = _os.getenv("EXPERT_FALLBACK_ON_RATELIMIT", "true").strip().lower() == "true"
                        except Exception:
                            allow_fb = True
                        err_text = str(e)
                        is_rate_limited = ("429" in err_text) or ("ReachLimit" in err_text) or ("concurrent" in err_text.lower())
                        time_left = budget_deadline - time.time()
                        if allow_fb and is_rate_limited and time_left > 3.0:
                            # Try fallback to Kimi provider quickly
                            try:
                                send_progress(f"{self.get_name()}: Rate-limited on {provider.get_provider_type().value}, starting cost-aware fallback...")
                            except Exception:
                                pass
                            try:
                                from utils.model_router import get_fallback_choice
                                from src.providers.registry import ModelProviderRegistry
                                fb_provider_type, fb_model = get_fallback_choice(provider.get_provider_type(), self.get_name())
                                fb_provider = ModelProviderRegistry.get_provider(fb_provider_type) if fb_provider_type else None
                            except Exception:
                                fb_provider = None
                                fb_model = None
                            if fb_provider and fb_model:
                                def _invoke_fb():
                                    return fb_provider.generate_content(
                                        prompt=prompt,
                                        model_name=fb_model,
                                        system_prompt=system_prompt,
                                        temperature=validated_temperature,
                                        thinking_mode=self.get_request_thinking_mode(request),
                                        use_websearch=self.get_request_use_websearch(request),
                                        images=list(set(self.consolidated_findings.images)) if self.consolidated_findings.images else None,
                                    )
                                fb_task = loop.run_in_executor(None, _invoke_fb)
                                # Wait within remaining time, emitting heartbeats
                                while True:
                                    if fb_task.done():
                                        model_response = fb_task.result()
                                        break
                                    if time.time() >= budget_deadline:
                                        logger.error("Expert analysis fallback exceeded time budget; returning partial result")
                                        return {"status":"analysis_timeout","error":"Expert analysis exceeded time budget","provider": (fb_provider.get_provider_type().value if fb_provider else "unknown"),"elapsed_seconds": round(max(0, time.time()-start_time), 2),"raw_analysis":""}
                                    try:
                                        send_progress(f"{self.get_name()}: Waiting on expert analysis (provider={fb_provider.get_provider_type().value})...")
                                    except Exception:
                                        pass
                                    await asyncio.sleep(hb)
                                break
                        # No fallback or still failing - re-raise to outer handler
                        raise
                    break
                now = time.time()
                if now >= budget_deadline:
                    logger.error("Expert analysis exceeded time budget; returning partial result")
                    return {
                        "status": "analysis_timeout",
                        "error": "Expert analysis exceeded time budget",
                        "provider": provider.get_provider_type().value if provider else "unknown",
                        "elapsed_seconds": round(max(0, time.time()-start_time), 2),
                        "raw_analysis": "",
                    }
                # Emit heartbeat at configured cadence
                try:
                    send_progress(f"{self.get_name()}: Waiting on expert analysis (provider={provider.get_provider_type().value})...")
                except Exception:
                    pass
                await asyncio.sleep(hb)


            if model_response.content:
                try:
                    analysis_result = json.loads(model_response.content.strip())
                    return analysis_result
                except json.JSONDecodeError:
                    # Check if this looks like Markdown content (expected for some tools)
                    content = model_response.content.strip()
                    if content.startswith('#') or '##' in content or '**' in content:
                        parse_info = "Response in Markdown format (expected for this tool)"
                    else:
                        parse_info = "Response was not valid JSON"

                    return {
                        "status": "analysis_complete",
                        "raw_analysis": model_response.content,
                        "parse_info": parse_info,
                    }
            else:
                return {"error": "No response from model", "status": "empty_response"}

        except Exception as e:
            logger.error(f"Error calling expert analysis: {e}", exc_info=True)
            return {"error": str(e), "status": "analysis_error"}

    def _process_work_step(self, step_data: dict):
        """
        Process a single work step and update internal state.

        This method is useful for testing and manual step processing.
        It adds the step to work history and updates consolidated findings.

        Args:
            step_data: Dictionary containing step information including:
                      step, step_number, findings, files_checked, etc.
        """
        # Store in history
        self.work_history.append(step_data)

        # Update consolidated findings
        self._update_consolidated_findings(step_data)

    # Common execute method for workflow-based tools

    async def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """
        Common execute logic for workflow-based tools.

        This method provides common validation and delegates to execute_workflow.
        Tools that need custom execute logic can override this method.
        """
        try:
            # Common validation
            if not arguments:
                error_data = {"status": "error", "content": "No arguments provided"}
                # Add basic metadata even for validation errors
                error_data["metadata"] = {"tool_name": self.get_name()}
                return [TextContent(type="text", text=json.dumps(error_data, ensure_ascii=False))]

            # Delegate to execute_workflow
            return await self.execute_workflow(arguments)

        except Exception as e:
            logger.error(f"Error in {self.get_name()} tool execution: {e}", exc_info=True)
            error_data = {
                "status": "error",
                "content": f"Error in {self.get_name()}: {str(e)}",
            }  # Add metadata to error responses
            self._add_workflow_metadata(error_data, arguments)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(error_data, ensure_ascii=False),
                )
            ]

    # Default implementations for methods that workflow-based tools typically don't need

    async def prepare_prompt(self, request) -> str:
        """
        Base implementation for workflow tools - compatible with BaseTool signature.

        Workflow tools typically don't need to return a prompt since they handle
        their own prompt preparation internally through the workflow execution.

        Args:
            request: The validated request object

        Returns:
            Empty string since workflow tools manage prompts internally
        """
        # Workflow tools handle their prompts internally during workflow execution
        return ""

    def format_response(self, response: str, request, model_info=None):
        """
        Workflow tools handle their own response formatting.
        The BaseWorkflowMixin formats responses internally.
        """
        return response
