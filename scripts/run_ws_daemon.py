# DEPRECATED SHIM — use scripts/ws/run_ws_daemon.py
# This top-level wrapper forwards to the canonical entry point and will be removed in a future release.

# Back-compat shim: prefer canonical script in subfolder; this shim forwards and exits.
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "ws" / "run_ws_daemon.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)

#!/usr/bin/env python
import sys
from pathlib import Path

# Ensure repository root is on sys.path
_repo_root = Path(__file__).resolve().parents[1]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Load .env to ensure EXAI_WS_* are available when run directly
try:
    from dotenv import load_dotenv  # type: ignore
    _env_path = _repo_root / ".env"
    if _env_path.exists():
        load_dotenv(str(_env_path))
except Exception:
    pass

from src.daemon.ws_server import main

if __name__ == "__main__":
    main()

