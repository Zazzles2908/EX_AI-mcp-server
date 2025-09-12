from __future__ import annotations

from enum import Enum
from typing import Any, Dict


class TaskType(Enum):
    VISUAL_ANALYSIS = "visual_analysis"
    LONG_CONTEXT_ANALYSIS = "long_context_analysis"
    CODE_GENERATION = "code_generation"
    MULTIMODAL_REASONING = "multimodal_reasoning"
    COMPLEX_WORKFLOWS = "complex_workflows"


class IntelligentTaskRouter:
    """Route tasks to a platform based on simple heuristics.

    This is scaffolding only. Real classification and provider calls will be
    added later. Keep logic deterministic and unit-testable without exai.
    """

    def __init__(self) -> None:
        self.routing_rules: Dict[TaskType, str] = {
            TaskType.VISUAL_ANALYSIS: "zai",
            TaskType.LONG_CONTEXT_ANALYSIS: "moonshot",
            TaskType.CODE_GENERATION: "moonshot",
            TaskType.MULTIMODAL_REASONING: "zai",
            TaskType.COMPLEX_WORKFLOWS: "hybrid",
        }

    def estimate_context_length(self, request: Dict[str, Any]) -> int:
        # Very rough token estimate: characters // 4 for 'messages' text
        messages = request.get("messages", [])
        total_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m, dict))
        return total_chars // 4

    def has_multimodal_content(self, request: Dict[str, Any]) -> bool:
        # If any message contains an 'images' key or non-text content marker
        return any("images" in m for m in request.get("messages", []) if isinstance(m, dict))

    def classify(self, request: Dict[str, Any]) -> TaskType:
        if self.has_multimodal_content(request):
            return TaskType.MULTIMODAL_REASONING
        if self.estimate_context_length(request) > 128_000:
            return TaskType.LONG_CONTEXT_ANALYSIS
        return TaskType.CODE_GENERATION

    def select_platform(self, request: Dict[str, Any]) -> str:
        task_type = self.classify(request)
        if task_type == TaskType.LONG_CONTEXT_ANALYSIS:
            return "moonshot"
        if task_type == TaskType.MULTIMODAL_REASONING:
            return "zai"
        return self.routing_rules.get(task_type, "moonshot")

