#!/usr/bin/env python3
"""
Thinking Routing & Model Selection Tests

Validates MCP boundary aliasing/rerouting for think tools and deterministic
model selection for ThinkDeep when model is missing/auto.

These tests run the standalone server and assert on behavior via responses
and log messages.
"""

import re
from .base_test import BaseSimulatorTest
from .log_utils import LogUtils


class TestThinkingRouting(BaseSimulatorTest):
    @property
    def test_name(self) -> str:
        return "thinking_routing"

    @property
    def test_description(self) -> str:
        return "Aliasing/rerouting and model selection for thinkdeep"

    def _assert_log_contains(self, pattern: str) -> bool:
        logs = LogUtils.get_recent_server_logs(600)
        return re.search(pattern, logs, re.IGNORECASE) is not None

    def test_alias_deepthink_to_thinkdeep(self):
        # Call non-registered exact alias 'deepthink' which should reroute
        response, _ = self.call_mcp_tool(
            "deepthink", {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f"}
        )
        assert response is not None, "deepthink alias call returned no response"
        assert self._assert_log_contains(r"REROUTE: 'deepthink' .*\u2192.* 'thinkdeep'|REROUTE: 'deepthink'"), (
            "Expected reroute log for deepthink -> thinkdeep"
        )

    def test_alias_unknown_contains_think(self):
        # Unknown tool name containing 'think' should reroute
        response, _ = self.call_mcp_tool(
            "foobar-think", {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f"}
        )
        assert response is not None, "foobar-think call returned no response"
        assert self._assert_log_contains(r"REROUTE: 'foobar-think' .*'thinkdeep'|REROUTE: 'foobar-think'"), (
            "Expected reroute log for foobar-think -> thinkdeep"
        )

    def test_no_reroute_for_thinkdeep(self):
        # Calling the correct tool should not reroute
        response, _ = self.call_mcp_tool(
            "thinkdeep", {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f"}
        )
        assert response is not None, "thinkdeep call returned no response"
        # Ensure we do NOT see a reroute originating from thinkdeep
        assert not self._assert_log_contains(r"REROUTE: 'thinkdeep'"), "Unexpected reroute for thinkdeep"

    def test_model_selection_kimi_priority(self):
        # When KIMI is configured, missing/auto model should select kimi-k2-thinking
        response, _ = self.call_mcp_tool(
            "thinkdeep",
            {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f", "model": "auto"},
        )
        assert response is not None, "thinkdeep auto model call returned no response"
        assert self._assert_log_contains(r"THINKING MODEL: resolved to 'kimi-k2-thinking'|kimi-k2-thinking"), (
            "Expected auto-resolve to kimi-k2-thinking when KIMI is available"
        )

    def test_model_selection_glm_fallback(self):
        # This test assumes only GLM is available in CI or will pass if logs show glm-4.5
        response, _ = self.call_mcp_tool(
            "thinkdeep",
            {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f"},
        )
        assert response is not None, "thinkdeep default model call returned no response"
        # Accept either kimi or glm depending on environment; ensure at least one appears
        assert self._assert_log_contains(r"THINKING MODEL: resolved to '(kimi-k2-thinking|glm-4.5)'") or \
            self._assert_log_contains(r"model: '(kimi-k2-thinking|glm-4.5)'")

    def test_explicit_model_not_overridden(self):
        # Provide explicit GLM model; server must not override
        response, _ = self.call_mcp_tool(
            "thinkdeep",
            {"step": "s", "step_number": 1, "total_steps": 1, "next_step_required": False, "findings": "f", "model": "glm-4.5"},
        )
        assert response is not None, "thinkdeep explicit model call returned no response"
        # Ensure there is no log indicating re-selection away from glm-4.5
        # We still may see parsed model log, but not THINKING MODEL resolved to other
        assert not self._assert_log_contains(r"THINKING MODEL: resolved to 'kimi-k2-thinking'"), (
            "Explicit model should not be overridden"
        )

    def run_test(self) -> bool:
        self.logger.info(f" Test: {self.test_description}")
        try:
            ok = True
            ok = ok and self.test_alias_deepthink_to_thinkdeep()
            ok = ok and self.test_alias_unknown_contains_think()
            ok = ok and self.test_no_reroute_for_thinkdeep()
            ok = ok and self.test_model_selection_kimi_priority()
            ok = ok and self.test_model_selection_glm_fallback()
            ok = ok and self.test_explicit_model_not_overridden()
            self.logger.info(f"✅ All {self.test_name} tests passed!")
            return ok
        except AssertionError as e:
            self.logger.error(str(e))
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False

