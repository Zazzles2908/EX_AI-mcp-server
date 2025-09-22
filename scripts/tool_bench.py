# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "validation" / "tool_bench.py"
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
EX MCP Server - Direct Tool Test Bench

Allows developers to list and invoke tools directly without a full MCP client.
This preserves MCP compatibility by importing the same tool implementations used by the server.

Examples:
  python scripts/tool_bench.py list
  python scripts/tool_bench.py run chat --json '{"prompt":"Hello","model":"kimi-k2-0711-preview"}'
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

# Ensure project root on path
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# Load .env if present
try:
    from dotenv import load_dotenv

    env_path = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
except Exception:
    pass

# Import tool registry the same way server.py does
try:
    from tools.registry import ToolRegistry  # preferred lean registry
except Exception:
    ToolRegistry = None

from tools import (
    AnalyzeTool,
    ChallengeTool,
    ChatTool,
    CodeReviewTool,
    ConsensusTool,
    DebugIssueTool,
    DocgenTool,
    ListModelsTool,
    PlannerTool,
    PrecommitTool,
    RefactorTool,
    SecauditTool,
    TestGenTool,
    ThinkDeepTool,
    TracerTool,
    VersionTool,
)


def build_tools() -> dict[str, Any]:
    # Try lean registry first
    if ToolRegistry is not None:
        try:
            reg = ToolRegistry()
            reg.build_tools()
            return reg.list_tools()
        except Exception:
            pass
    # Fallback static set (match server.py)
    return {
        "chat": ChatTool(),
        "thinkdeep": ThinkDeepTool(),
        "planner": PlannerTool(),
        "consensus": ConsensusTool(),
        "codereview": CodeReviewTool(),
        "precommit": PrecommitTool(),
        "debug": DebugIssueTool(),
        "analyze": AnalyzeTool(),
        "refactor": RefactorTool(),
        "tracer": TracerTool(),
        "testgen": TestGenTool(),
        "secaudit": SecauditTool(),
        "docgen": DocgenTool(),
        "listmodels": ListModelsTool(),
        "version": VersionTool(),
        "challenge": ChallengeTool(),
    }


def run_tool(tool_name: str, args_json: str) -> int:
    tools = build_tools()
    if tool_name not in tools:
        print(f"Unknown tool: {tool_name}. Available: {', '.join(sorted(tools.keys()))}")
        return 2
    try:
        arguments = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError as e:
        print(f"Invalid JSON for --json: {e}")
        return 3

    tool = tools[tool_name]
    # Tools implement async execute; run with asyncio
    import asyncio

    async def _run():
        res = await tool.execute(arguments)
        # Results are typically list[TextContent] or strings
        if isinstance(res, list):
            # Attempt to render mcp TextContent objects
            out = []
            for item in res:
                try:
                    if hasattr(item, "type") and getattr(item, "type", None) == "text":
                        out.append(item.text)
                    else:
                        out.append(str(item))
                except Exception:
                    out.append(str(item))
            print("\n".join(out))
        else:
            print(res)

    asyncio.run(_run())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="EX MCP Server Tool Bench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List all available tools")

    p_run = sub.add_parser("run", help="Run a tool with JSON args")
    p_run.add_argument("tool", help="Tool name (e.g., chat, analyze, thinkdeep)")
    p_run.add_argument("--json", default="{}", help="JSON arguments for the tool")

    args = parser.parse_args()

    if args.cmd == "list":
        tools = build_tools()
        print("Available tools:\n" + "\n".join(sorted(tools.keys())))
        return 0
    elif args.cmd == "run":
        return run_tool(args.tool, args.json)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())

