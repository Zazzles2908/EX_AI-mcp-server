#!/usr/bin/env python3
"""
EX-AI MCP WS Stack Diagnoser

Purpose: One-stop diagnosis for WebSocket daemon + stdio shim + classic wrapper.
- Prints clear PASS/FAIL per check with actionable hints
- Reads .env automatically (or ENV_FILE override)
- Validates files, env, venv, Python packages
- Tests WS daemon reachability (hello, list_tools, version)
- Tests shim as an MCP stdio server (initialize, list_tools)
- Validates Augment mcp-config.augmentcode.json entries (paths, args, cwd)

Safe to run: does not modify state. Network access only to ws://EXAI_WS_HOST:EXAI_WS_PORT.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Repo root
ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"
LOGS = ROOT / "logs"
ENV_FILE = os.getenv("ENV_FILE") or str(ROOT / ".env")

# Load .env early for consistent behavior across classic and daemon paths
try:
    from dotenv import load_dotenv  # type: ignore
    if os.path.exists(ENV_FILE):
        load_dotenv(dotenv_path=ENV_FILE)
    else:
        # Fallback to repo .env
        fallback_env = ROOT / ".env"
        if fallback_env.exists():
            load_dotenv(dotenv_path=str(fallback_env))
except Exception:
    pass

WS_HOST = os.getenv("EXAI_WS_HOST", "127.0.0.1")
WS_PORT = int(os.getenv("EXAI_WS_PORT", "8765"))
WS_TOKEN = os.getenv("EXAI_WS_TOKEN", "")

@dataclass
class Check:
    name: str
    ok: bool
    info: str = ""
    hint: str = ""

RESULTS: list[Check] = []

def add(name: str, ok: bool, info: str = "", hint: str = "") -> None:
    RESULTS.append(Check(name, ok, info, hint))
    status = "PASS" if ok else "FAIL"
    print(f"- {name:20s} {status} :: {info or hint}")


def section(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def check_files() -> None:
    section("1) Files & Structure")
    expected = {
        "server.py": ROOT / "server.py",
        "scripts/run_ws_shim.py": ROOT / "scripts" / "run_ws_shim.py",
        "scripts/run_ws_daemon.py": ROOT / "scripts" / "run_ws_daemon.py",
        "scripts/mcp_server_wrapper.py": ROOT / "scripts" / "mcp_server_wrapper.py",
        "src/daemon/ws_server.py": ROOT / "src" / "daemon" / "ws_server.py",
        "tools/ws_daemon_smoke.py": ROOT / "tools" / "ws_daemon_smoke.py",
        "mcp-config.augmentcode.json": ROOT / "mcp-config.augmentcode.json",
    }
    ok = True
    for label, path in expected.items():
        exists = path.exists()
        print(f"  {label:32s} exists={exists} path={path}")
        ok = ok and exists
    add("structure", ok, hint="Create missing paths or fix repo layout")


def check_python_env() -> None:
    section("2) Python & VENV")
    try:
        py = sys.executable
        print("  python:", py)
        print("  version:", sys.version)
        if VENV_PY.exists():
            add("venv", True, info=f"VENV present: {VENV_PY}")
        else:
            add("venv", False, hint="Create .venv and install deps")
    except Exception as e:
        add("python", False, hint=str(e))


def check_packages() -> None:
    section("3) Packages")
    ok = True
    try:
        import websockets  # noqa: F401
    except Exception as e:
        ok = False
        print("  websockets missing:", e)
    try:
        from mcp.server import Server  # noqa: F401
        from mcp.client.stdio import stdio_client, StdioServerParameters  # noqa: F401
        from mcp.client.session import ClientSession  # noqa: F401
    except Exception as e:
        ok = False
        print("  mcp package issue:", e)
    add("packages", ok, hint="Install 'websockets' and 'mcp' in the venv")


def check_env() -> None:
    section("4) Environment")
    keys = [
        "ENV_FILE", "LOG_LEVEL", "DEFAULT_MODEL",
        "KIMI_API_KEY", "GLM_API_KEY",
        "EXAI_WS_HOST", "EXAI_WS_PORT", "EXAI_WS_TOKEN",
    ]
    for k in keys:
        v = os.getenv(k)
        shown = ("[SET]" if ("_KEY" in k and v) else (v if v else "[MISSING]"))
        print(f"  {k:16s} = {shown}")
    add("env", True, info=".env processed and inspected")


async def test_ws_daemon() -> bool:
    import websockets
    uri = f"ws://{WS_HOST}:{WS_PORT}"
    try:
        async with websockets.connect(uri) as ws:
            await ws.send(json.dumps({"op": "hello", "session_id": "diag", "token": WS_TOKEN}))
            ack = json.loads(await ws.recv())
            if not ack.get("ok"):
                print("  hello failed:", ack)
                return False
            await ws.send(json.dumps({"op": "list_tools"}))
            tools = json.loads(await ws.recv())
            names = [t.get("name") for t in tools.get("tools", [])]
            print(f"  WS tools: {len(names)}")
            if "version" in names:
                rid = "diag-version"
                await ws.send(json.dumps({"op": "call_tool", "request_id": rid, "name": "version", "arguments": {}}))
                while True:
                    msg = json.loads(await ws.recv())
                    if msg.get("op") == "call_tool_res" and msg.get("request_id") == rid:
                        if msg.get("error"):
                            print("  version error:", msg.get("error"))
                        else:
                            outs = msg.get("outputs") or []
                            text = outs[0].get("text")[:120] if outs else "<none>"
                            print("  version ok:", text)
                        break
        return True
    except Exception as e:
        print("  WS test failed:", e)
        return False


async def test_stdio_shim() -> bool:
    try:
        from mcp.client.stdio import stdio_client, StdioServerParameters
        from mcp.client.session import ClientSession
    except Exception as e:
        print("  mcp client not available:", e)
        return False
    cmd = str(VENV_PY if VENV_PY.exists() else sys.executable)
    shim = str(ROOT / "scripts" / "run_ws_shim.py")
    env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8", "LOG_LEVEL": os.getenv("LOG_LEVEL", "DEBUG")}
    try:
        async with stdio_client(StdioServerParameters(command=cmd, args=["-u", shim], cwd=str(ROOT), env=env)) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=20)
                tools = await asyncio.wait_for(session.list_tools(), timeout=20)
                print("  Shim MCP tools:", len(tools.tools))
                return True
    except Exception as e:
        print("  Shim MCP test failed:", e)
        return False


def check_mcp_config() -> None:
    section("5) Augment MCP Config")
    path = ROOT / "mcp-config.augmentcode.json"
    if not path.exists():
        add("mcp_config", False, hint="mcp-config.augmentcode.json missing")
        return
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        servers = (cfg.get("mcpServers") or {})
        exai_ws = servers.get("EXAI-WS") or {}
        cmd = exai_ws.get("command"); args = exai_ws.get("args") or []; cwd = exai_ws.get("cwd")
        abs_ok = all([(isinstance(a, str) and (":/" in a or ":\\" in a or a.endswith(".py") and (ROOT / a).exists())) for a in args])
        print("  EXAI-WS:")
        print("    command:", cmd)
        print("    args:", args)
        print("    cwd:", cwd)
        if not abs_ok:
            print("    NOTE: some args look relative; prefer absolute path to run_ws_shim.py on Windows.")
        add("mcp_config", True, info="Parsed EXAI-WS entry")
    except Exception as e:
        add("mcp_config", False, hint=f"Parse failed: {e}")


def summarize() -> int:
    section("Summary")
    bad = [r for r in RESULTS if not r.ok]
    for r in RESULTS:
        status = "PASS" if r.ok else "FAIL"
        print(f"  {status:4s} - {r.name}: {r.info or r.hint}")
    print("\nOVERALL:", "OK" if not bad else "ATTENTION NEEDED")
    return 0 if not bad else 1


def main() -> int:
    print(f"EX WS Stack Diagnostics — {ROOT}")
    check_files()
    check_python_env()
    check_packages()
    check_env()
    # Async tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("\n6) WS Daemon Test")
    ok_ws = loop.run_until_complete(test_ws_daemon())
    add("ws_daemon", ok_ws, hint="Start run_ws_daemon.py and ensure EXAI_WS_* env")
    print("\n7) Stdio Shim (MCP) Test")
    ok_shim = loop.run_until_complete(test_stdio_shim())
    add("stdio_shim", ok_shim, hint="Fix stdio launch (args/cwd/encoding) or see Augment Output")
    check_mcp_config()
    return summarize()


if __name__ == "__main__":
    sys.exit(main())

