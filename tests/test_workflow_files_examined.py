from __future__ import annotations

import types

from tools.workflow.workflow_mixin import BaseWorkflowMixin


class DummyTool(BaseWorkflowMixin):
    def get_name(self) -> str: return "dummy"
    def get_workflow_request_model(self) -> type: return type("Req", (), {})
    def get_system_prompt(self) -> str: return ""
    def get_language_instruction(self) -> str: return ""
    def get_default_temperature(self) -> float: return 0.2
    def get_model_provider(self, model_name: str): return None
    def _resolve_model_context(self, arguments, request): return ("auto", None)
    def _prepare_file_content_for_prompt(self, request_files, continuation_id, context_description="New files", max_tokens=None, reserve_tokens=1000, remaining_budget=None, arguments=None, model_context=None):
        # Return processed files unchanged to simulate embedding
        return ("CONTENT", list(request_files))
    def get_work_steps(self, request): return []
    def get_required_actions(self, step_number, confidence, findings, total_steps): return []
    def requires_expert_analysis(self) -> bool: return True
    def should_include_files_in_expert_prompt(self) -> bool: return False


def test_files_examined_updates_on_embed():
    tool = DummyTool()

    class Req:
        step = "s"
        step_number = 1
        total_steps = 1
        next_step_required = False  # final step triggers embedding
        findings = "f"
        relevant_files = ["a.py", "b.py"]
        images = []

    # Execute the critical embedding path
    tool._handle_workflow_file_context(Req, {"_model_context": types.SimpleNamespace(provider=None)})

    # After embedding, files_examined should include actually processed files
    assert {"a.py", "b.py"}.issubset(tool.consolidated_findings.files_checked)

