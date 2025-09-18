import pytest

try:
    from tools.consensus import ConsensusRequest
except Exception:  # Fallback for different project layouts
    ConsensusRequest = None


@pytest.mark.skipif(ConsensusRequest is None, reason="Consensus tool not available in this layout")
def test_step1_requires_findings():
    # Step 1 without findings should fail validation
    with pytest.raises(Exception):
        ConsensusRequest(
            step="1",
            step_number=1,
            total_steps=2,
            next_step_required=True,
            findings=None,
        )

