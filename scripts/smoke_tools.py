# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "validation" / "smoke_tools.py"
    try:
        runpy.run_path(str(target), run_name="__main__")
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"Shim failed to run target {target}: {e}")
        sys.exit(1)
    sys.exit(0)


import asyncio
import os
import sys

# Ensure repo root on sys.path
_repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

# Import server and ensure providers are configured
import server
from server import handle_call_tool

try:
    # Prefer .env if present
    try:
        from dotenv import load_dotenv  # type: ignore
        load_dotenv(os.path.join(_repo_root, ".env"))
    except Exception:
        pass
    # Configure providers (lazy guard also runs inside handle_call_tool)
    if hasattr(server, "configure_providers"):
        server.configure_providers()
except Exception as e:
    print("[WARN] Provider configuration error:", e)

async def call_tool(name: str, args: dict):
    try:
        out = await handle_call_tool(name, args)
        texts = [getattr(c, "text", getattr(c, "content", "")) for c in out]
        return "\n".join([t for t in texts if isinstance(t, str)])
    except Exception as e:
        return f"ERROR calling {name}: {e}"

async def main():
    print("=== Smoke: listmodels ===")
    print(await call_tool("listmodels", {}))

    print("\n=== Smoke: provider_capabilities ===")
    print(await call_tool("provider_capabilities", {"include_tools": True}))

    print("\n=== Smoke: version ===")
    print(await call_tool("version", {}))

if __name__ == "__main__":
    asyncio.run(main())

