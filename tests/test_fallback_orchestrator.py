import json
import unittest

# We avoid importing mcp.types in tests; fallback_orchestrator only uses getattr(..., 'text')
from src.server.fallback_orchestrator import _is_error_envelope


class FakeText:
    def __init__(self, text: str):
        self.text = text


class TestFallbackIsErrorEnvelope(unittest.TestCase):
    def test_empty_list_returns_false(self):
        self.assertFalse(_is_error_envelope([]))

    def test_success_with_content_returns_false(self):
        envelope = {"status": "success", "content": "ok"}
        self.assertFalse(_is_error_envelope([FakeText(json.dumps(envelope))]))

    def test_success_empty_content_returns_false(self):
        envelope = {"status": "success", "content": ""}
        self.assertFalse(_is_error_envelope([FakeText(json.dumps(envelope))]))

    def test_explicit_error_status_returns_true(self):
        for status in ("execution_error", "cancelled", "failed", "timeout", "error"):
            envelope = {"status": status, "error": "x"}
            self.assertTrue(_is_error_envelope([FakeText(json.dumps(envelope))]), status)

    def test_plain_text_non_json_returns_false(self):
        self.assertFalse(_is_error_envelope([FakeText("plain text ok")]))

    def test_error_field_returns_true(self):
        envelope = {"status": "unknown", "error": "boom"}
        self.assertTrue(_is_error_envelope([FakeText(json.dumps(envelope))]))


if __name__ == "__main__":
    unittest.main(verbosity=2)

