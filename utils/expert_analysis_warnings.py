"""
Expert Analysis Cost Warning Utilities

Provides utilities for warning users about API costs when expert analysis
is about to be performed by workflow tools.
"""

import logging
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ExpertAnalysisCostWarning:
    """Utility class for generating cost warnings for expert analysis."""
    
    # Estimated costs per 1K tokens (approximate, for warning purposes only)
    ESTIMATED_COSTS = {
        "glm-4.5-flash": 0.0001,  # Very low cost
        "glm-4.5": 0.0005,
        "glm-4.5-air": 0.0003,
        "kimi-k2-turbo-preview": 0.0002,
        "kimi-k2-0711-preview": 0.0008,
        "moonshot-v1-8k": 0.0012,
        "moonshot-v1-32k": 0.0012,
        "moonshot-v1-128k": 0.0012,
        "default": 0.0005,  # Conservative estimate
    }
    
    @classmethod
    def should_show_warning(cls) -> bool:
        """
        Determine if cost warnings should be shown.
        
        Returns True if warnings are enabled via environment variable.
        """
        return os.getenv("EXPERT_ANALYSIS_SHOW_WARNINGS", "true").lower() == "true"
    
    @classmethod
    def estimate_cost(cls, model_name: str, estimated_tokens: int) -> float:
        """
        Estimate the cost of expert analysis for a given model and token count.
        
        Args:
            model_name: Name of the model to be used
            estimated_tokens: Estimated number of tokens to be processed
            
        Returns:
            Estimated cost in USD
        """
        cost_per_1k = cls.ESTIMATED_COSTS.get(model_name, cls.ESTIMATED_COSTS["default"])
        return (estimated_tokens / 1000) * cost_per_1k
    
    @classmethod
    def generate_warning_message(
        cls,
        model_name: str,
        estimated_tokens: int,
        file_count: int,
        tool_name: str
    ) -> str:
        """
        Generate a comprehensive warning message about expert analysis costs.
        
        Args:
            model_name: Name of the model to be used
            estimated_tokens: Estimated number of tokens to be processed
            file_count: Number of files that will be sent to the API
            tool_name: Name of the tool requesting expert analysis
            
        Returns:
            Formatted warning message
        """
        estimated_cost = cls.estimate_cost(model_name, estimated_tokens)
        
        warning_parts = [
            "WARNING: EXPERT ANALYSIS COST WARNING",
            "",
            f"The {tool_name} tool is about to perform expert analysis which will:",
            "",
            "SEND DATA TO EXTERNAL API:",
            f"   - {file_count} file(s) will be sent to {model_name}",
            f"   - Estimated {estimated_tokens:,} tokens to be processed",
            f"   - Estimated cost: ~${estimated_cost:.4f} USD",
            "",
            "PRIVACY NOTICE:",
            "   - File content will be sent to external AI service",
            "   - Data may be processed on external servers",
            "   - Review your API provider's privacy policy",
            "",
            "TO AVOID COSTS:",
            "   - Set use_assistant_model=false in your request",
            "   - Or set DEFAULT_USE_ASSISTANT_MODEL=false in .env",
            "",
            "Expert analysis provides additional validation but is optional.",
            "The tool can complete successfully without it."
        ]
        
        return "\n".join(warning_parts)
    
    @classmethod
    def generate_completion_message(
        cls,
        model_name: str,
        actual_tokens: int,
        tool_name: str,
        expert_analysis_used: bool
    ) -> str:
        """
        Generate a completion message showing actual costs incurred.
        
        Args:
            model_name: Name of the model that was used
            actual_tokens: Actual number of tokens processed
            tool_name: Name of the tool that completed
            expert_analysis_used: Whether expert analysis was actually performed
            
        Returns:
            Formatted completion message
        """
        if not expert_analysis_used:
            return (
                f"{tool_name} completed without expert analysis.\n"
                "No additional API costs incurred."
            )

        actual_cost = cls.estimate_cost(model_name, actual_tokens)

        return (
            f"{tool_name} completed with expert analysis.\n"
            f"Estimated cost: ~${actual_cost:.4f} USD ({actual_tokens:,} tokens via {model_name})"
        )
    
    @classmethod
    def get_cost_control_instructions(cls) -> str:
        """
        Get instructions for controlling expert analysis costs.
        
        Returns:
            Formatted instructions for cost control
        """
        return (
            "EXPERT ANALYSIS COST CONTROL:\n"
            "\n"
            "Per-request control:\n"
            "  - Add use_assistant_model=false to disable for this request\n"
            "  - Add use_assistant_model=true to enable for this request\n"
            "\n"
            "Global control (.env file):\n"
            "  - DEFAULT_USE_ASSISTANT_MODEL=false (disable by default)\n"
            "  - DEFAULT_USE_ASSISTANT_MODEL=true (enable by default)\n"
            "\n"
            "Warning control:\n"
            "  - EXPERT_ANALYSIS_SHOW_WARNINGS=false (hide warnings)\n"
            "  - EXPERT_ANALYSIS_SHOW_WARNINGS=true (show warnings)\n"
            "\n"
            "Tools that support expert analysis:\n"
            "  - analyze, codereview, debug, thinkdeep, secaudit, refactor, testgen\n"
            "\n"
            "Tools that are self-contained (no expert analysis):\n"
            "  - planner, consensus, docgen, chat, activity"
        )


def should_warn_about_expert_analysis() -> bool:
    """
    Check if expert analysis warnings should be shown.
    
    Returns:
        True if warnings should be shown, False otherwise
    """
    return ExpertAnalysisCostWarning.should_show_warning()


def format_expert_analysis_warning(
    model_name: str,
    estimated_tokens: int,
    file_count: int,
    tool_name: str
) -> str:
    """
    Format a warning message about expert analysis costs.
    
    Args:
        model_name: Name of the model to be used
        estimated_tokens: Estimated number of tokens to be processed
        file_count: Number of files that will be sent to the API
        tool_name: Name of the tool requesting expert analysis
        
    Returns:
        Formatted warning message
    """
    return ExpertAnalysisCostWarning.generate_warning_message(
        model_name, estimated_tokens, file_count, tool_name
    )


def format_expert_analysis_completion(
    model_name: str,
    actual_tokens: int,
    tool_name: str,
    expert_analysis_used: bool
) -> str:
    """
    Format a completion message showing actual costs incurred.
    
    Args:
        model_name: Name of the model that was used
        actual_tokens: Actual number of tokens processed
        tool_name: Name of the tool that completed
        expert_analysis_used: Whether expert analysis was actually performed
        
    Returns:
        Formatted completion message
    """
    return ExpertAnalysisCostWarning.generate_completion_message(
        model_name, actual_tokens, tool_name, expert_analysis_used
    )


def get_expert_analysis_help() -> str:
    """
    Get help text for controlling expert analysis costs.
    
    Returns:
        Formatted help text
    """
    return ExpertAnalysisCostWarning.get_cost_control_instructions()
