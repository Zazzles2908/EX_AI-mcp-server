from __future__ import annotations

from tools.consensus import ConsensusTool


def test_findings_not_required_in_schema():
    tool = ConsensusTool()
    schema = tool.get_input_schema()

    assert "findings" in schema["properties"], "findings should be a property for documentation"
    assert "findings" not in schema["required"], "findings must not be required at schema level"


def test_next_call_omits_null_continuation_id():
    tool = ConsensusTool()
    # Build a minimal fake request object with needed attributes
    class Req:
        step = "Initial"
        step_number = 1
        total_steps = 1
        next_step_required = True
        findings = "x"
        images = []

    # No continuation id provided
    response = tool.build_base_response(Req, continuation_id=None)

    # continuation_id should not be present when None
    assert "continuation_id" not in response

    # next_call should also omit continuation_id when None
    assert "next_call" in response
    args = response["next_call"]["arguments"]
    assert "continuation_id" not in args

