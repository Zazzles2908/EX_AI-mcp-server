# DEPRECATED SHIM — use scripts/validation/ws_exercise_all_tools_noauth.py
# This top-level wrapper forwards to the canonical entry point and will be removed in a future release.

# Back-compat shim: prefer canonical script in subfolder; this shim forwards and exits.
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "validation" / "ws_exercise_all_tools_noauth.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)

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

