"""
Expert Analysis Configuration Tool

Provides a simple interface for users to understand and configure
expert analysis behavior across workflow tools.
"""

import logging
from typing import Any, Dict

from tools.shared.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ExpertAnalysisConfigTool(BaseTool):
    """Tool for managing expert analysis configuration."""

    def get_name(self) -> str:
        return "expert_analysis_config"

    def get_description(self) -> str:
        return (
            "View and understand expert analysis configuration. Shows current settings, "
            "cost implications, and how to control API usage for workflow tools."
        )

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "help", "costs"],
                    "description": "Action to perform: 'status' shows current config, 'help' shows control instructions, 'costs' shows cost information",
                    "default": "status"
                }
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the expert analysis configuration tool."""
        action = arguments.get("action", "status")
        
        try:
            if action == "status":
                return self._show_status()
            elif action == "help":
                return self._show_help()
            elif action == "costs":
                return self._show_costs()
            else:
                return {
                    "content": f"Unknown action: {action}. Use 'status', 'help', or 'costs'.",
                    "content_type": "text"
                }
        except Exception as e:
            logger.error(f"Expert analysis config tool error: {e}")
            return {
                "content": f"Error: {e}",
                "content_type": "text"
            }

    def _show_status(self) -> Dict[str, Any]:
        """Show current expert analysis configuration status."""
        try:
            from config.expert_analysis import get_expert_analysis_summary
            config_summary = get_expert_analysis_summary()
            
            status_parts = [
                "🔧 EXPERT ANALYSIS CONFIGURATION STATUS",
                "",
                "Global Settings:",
                f"  • Mode: {config_summary.get('global_mode', 'unknown')}",
                f"  • Show Warnings: {config_summary.get('global_warnings', 'unknown')}",
                f"  • Show Cost Summary: {config_summary.get('global_cost_summary', 'unknown')}",
                f"  • Timeout: {config_summary.get('global_timeout', 'unknown')} seconds",
                f"  • Heartbeat: {config_summary.get('global_heartbeat', 'unknown')} seconds",
            ]
            
            if 'global_cost_threshold' in config_summary:
                status_parts.append(f"  • Cost Threshold: {config_summary['global_cost_threshold']}")
            
            # Tool-specific overrides
            tool_overrides = {k: v for k, v in config_summary.items() if k.startswith('tool_')}
            if tool_overrides:
                status_parts.extend(["", "Tool-Specific Overrides:"])
                for key, value in tool_overrides.items():
                    tool_name = key.replace('tool_', '').replace('_mode', '')
                    status_parts.append(f"  • {tool_name}: {value}")
            
            status_parts.extend([
                "",
                "Workflow Tools with Expert Analysis:",
                "  • analyze - Code analysis and architectural assessment",
                "  • codereview - Comprehensive code review",
                "  • debug - Root cause analysis and bug hunting",
                "  • thinkdeep - Extended reasoning and investigation",
                "  • secaudit - Security audit and vulnerability assessment",
                "  • refactor - Code refactoring analysis",
                "  • testgen - Test generation and coverage analysis",
                "",
                "Self-Contained Tools (No Expert Analysis):",
                "  • planner - Planning and task breakdown",
                "  • consensus - Multi-model consensus building",
                "  • docgen - Documentation generation",
                "  • chat - General conversation",
                "  • activity - Server activity monitoring"
            ])
            
            return {
                "content": "\n".join(status_parts),
                "content_type": "text"
            }
            
        except Exception as e:
            return {
                "content": f"Failed to get configuration status: {e}",
                "content_type": "text"
            }

    def _show_help(self) -> Dict[str, Any]:
        """Show help for controlling expert analysis."""
        try:
            from utils.expert_analysis_warnings import get_expert_analysis_help
            help_text = get_expert_analysis_help()
            
            return {
                "content": help_text,
                "content_type": "text"
            }
            
        except Exception as e:
            return {
                "content": f"Failed to get help information: {e}",
                "content_type": "text"
            }

    def _show_costs(self) -> Dict[str, Any]:
        """Show cost information for expert analysis."""
        try:
            from utils.expert_analysis_warnings import ExpertAnalysisCostWarning
            
            cost_parts = [
                "💰 EXPERT ANALYSIS COST INFORMATION",
                "",
                "Estimated Costs per 1,000 tokens:",
            ]
            
            for model, cost in ExpertAnalysisCostWarning.ESTIMATED_COSTS.items():
                if model != "default":
                    cost_parts.append(f"  • {model}: ~${cost:.4f}")
            
            cost_parts.extend([
                "",
                "💡 Cost Factors:",
                "  • File size and number of files processed",
                "  • Model selected (flash models are cheaper)",
                "  • Conversation history length",
                "  • Complexity of analysis requested",
                "",
                "🎯 Cost Optimization Tips:",
                "  • Use DEFAULT_USE_ASSISTANT_MODEL=false for routine work",
                "  • Enable expert analysis only for critical reviews",
                "  • Use flash models (glm-4.5-flash, kimi-k2-turbo-preview)",
                "  • Limit file scope to essential files only",
                "  • Set cost thresholds with EXPERT_ANALYSIS_MAX_COST_THRESHOLD",
                "",
                "⚠️  Important Notes:",
                "  • Costs are estimates and may vary",
                "  • Actual costs depend on your API provider",
                "  • Expert analysis sends file content to external services",
                "  • Review your provider's privacy policy for data handling"
            ])
            
            return {
                "content": "\n".join(cost_parts),
                "content_type": "text"
            }
            
        except Exception as e:
            return {
                "content": f"Failed to get cost information: {e}",
                "content_type": "text"
            }
