# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "diagnostics" / "exai_diagnose.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


#!/usr/bin/env python3
"""
EX-AI MCP Diagnostic Script
- Verifies Python, .env presence, and provider key availability
- Optionally verifies server import and prints tool count
Run:
  py -3 EX-AI-MCP-Server/scripts/exai_diagnose.py
or
  python EX-AI-MCP-Server/scripts/exai_diagnose.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def print_kv(k, v):
    print(f"{k:24} {v}")


def main():
    print("=== EX-AI MCP Diagnose ===")
    print_kv("ROOT", str(ROOT))
    print_kv("CWD", str(Path.cwd()))

    # Python version
    print_kv("Python", sys.version.split(" ")[0])

    # .env presence
    print_kv(".env exists", ENV_PATH.exists())

    # Load .env manually (non-invasive)
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"\'')

    # Show provider keys (masked)
    def mask(val):
        if not val:
            return "<missing>"
        return val[:4] + "…" + val[-4:] if len(val) > 8 else "********"

    print_kv("KIMI_API_KEY", mask(env.get("KIMI_API_KEY")))
    print_kv("GLM_API_KEY", mask(env.get("GLM_API_KEY")))

    # Identity defaults from env
    print_kv("MCP_SERVER_ID", env.get("MCP_SERVER_ID", "exai-server (default)"))
    print_kv("MCP_SERVER_NAME", env.get("MCP_SERVER_NAME", "exai (default)"))

    # Try importing server if present
    server_py = ROOT / "server.py"
    if server_py.exists():
        print("\nserver.py found – basic import test…")
        try:
            sys.path.insert(0, str(ROOT))
            import server  # noqa: F401
            print("OK: server.py import succeeded")
        except Exception as e:
            print(f"WARN: server import failed: {e}")
    else:
        print("\nserver.py not found yet – did you run the clone/copy step?")
        print("Run:\n  pwsh -File EX-AI-MCP-Server/scripts/clone_from_zen.ps1")

    print("\nNext: auggie --mcp-config C:\\Project\\EX-AI-MCP-Server\\mcp-config.json")


if __name__ == "__main__":
    main()

