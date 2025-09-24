import sys
sys.path.append(".")
from utils.conversation_memory import ConversationMemory
from utils.file_utils import read_file_content

"""
Thread Context Management Module

This module handles conversation thread context reconstruction and management
for multi-turn AI conversations in the EX MCP Server.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

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
