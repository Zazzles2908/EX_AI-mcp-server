#!/usr/bin/env python3
"""
Smoke test for deferred expert analysis path.
- Calls analyze tool final step on docs/flags.md
- Prints immediate response
- If deferred, polls await_result until complete/error or 70s timeout
"""
import asyncio
import json
import os
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server import TOOLS, configure_providers  # noqa: E402
from utils.model_context import ModelContext  # noqa: E402


def main() -> int:
    configure_providers()

    analyze = TOOLS.get("analyze")
    await_result = TOOLS.get("await_result")
    if analyze is None or await_result is None:
        print("ERR: Tools not registered: analyze or await_result missing", file=sys.stderr)
        return 2

    params = {
        "step": "Final step (smoke)",
        "step_number": 1,
        "total_steps": 1,
        "next_step_required": False,
        "findings": "Validate deferred path",
        "relevant_files": [os.path.join(PROJECT_ROOT, "docs", "flags.md")],
        "use_assistant_model": True,
        "temperature": 0,
        "thinking_mode": "minimal",
        "use_websearch": False,
        "analysis_type": "general",
        "output_format": "summary",
        # Provide a minimal model context; name will be resolved inside tool if needed
        "_model_context": ModelContext("glm-4.5-flash"),
        "_resolved_model_name": "glm-4.5-flash",
    }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print("-- Calling analyze (final step) --", flush=True)
    res = loop.run_until_complete(analyze.execute(params))
    text = res[0].text if res and hasattr(res[0], "text") else (str(res[0]) if res else "")
    print("Analyze immediate response:")
    print(text)

    # Try to parse response
    try:
        payload = json.loads(text)
    except Exception as e:
        print(f"WARN: Could not parse analyze JSON: {e}")
        return 0

    expert = payload.get("expert_analysis", {}) if isinstance(payload, dict) else {}
    if expert.get("status") != "processing":
        print("-- Not deferred (blocking mode or completed immediately) --")
        return 0

    handle = expert.get("result_handle")
    if not handle:
        print("ERR: No result_handle provided in deferred response")
        return 3

    print(f"-- Polling await_result for handle={handle} --", flush=True)
    deadline = time.time() + 70
    last_status = None
    while time.time() < deadline:
        poll_res = loop.run_until_complete(await_result.execute({"result_handle": handle}))
        poll_text = poll_res[0].text if poll_res and hasattr(poll_res[0], "text") else (str(poll_res[0]) if poll_res else "")
        try:
            poll_payload = json.loads(poll_text)
        except Exception:
            print("WARN: Non-JSON await_result payload:", poll_text)
            time.sleep(2)
            continue
        status = poll_payload.get("status")
        if status != last_status:
            print(f"await_result status: {status}")
            last_status = status
        if status in ("complete", "error", "not_found"):
            print(json.dumps(poll_payload, ensure_ascii=False))
            return 0
        time.sleep(2)

    print("ERR: await_result polling timed out after 70s")
    return 4


if __name__ == "__main__":
    sys.exit(main())

