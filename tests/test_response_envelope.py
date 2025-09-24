import unittest

from src.utils.response_envelope import mcp_call_summary, response_normalized_len_line


class TestResponseEnvelope(unittest.TestCase):
    def test_mcp_call_summary_format(self):
        s = mcp_call_summary(
            tool="chat",
            status="COMPLETE",
            step_no=1,
            total_steps=None,
            duration_sec=12.34,
            model="glm-4.5-flash",
            tokens=321,
            continuation_id=None,
            expert_enabled=False,
            req_id="abc-123",
        )
        self.assertTrue(s.startswith("MCP_CALL_SUMMARY:"))
        self.assertIn("tool=chat", s)
        self.assertIn("status=COMPLETE", s)
        self.assertIn("step=1/?", s)
        self.assertIn("dur=12.3s", s)  # rounded to 1 decimal
        self.assertIn("model=glm-4.5-flash", s)
        self.assertIn("tokens~=321", s)
        self.assertIn("cont_id=-", s)
        self.assertIn("expert=Disabled", s)
        self.assertIn("req_id=abc-123", s)

    def test_response_normalized_len_line(self):
        line = response_normalized_len_line(tool="activity", req_id="xyz", length=1)
        self.assertEqual(
            line,
            "RESPONSE_DEBUG: normalized_result_len=1 tool=activity req_id=xyz",
        )


if __name__ == "__main__":
    unittest.main()

