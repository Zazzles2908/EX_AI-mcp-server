#!/usr/bin/env python
"""
Wrapper to exercise WS tools without sending EXAI_WS_TOKEN.
Useful when the daemon is configured to allow anonymous access.
"""
import os
import asyncio

# Force empty token for this process only
os.environ["EXAI_WS_TOKEN"] = ""

import ws_exercise_all_tools as w  # type: ignore

if __name__ == "__main__":
    raise SystemExit(asyncio.run(w.main()))

