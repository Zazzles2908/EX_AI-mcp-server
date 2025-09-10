import os
import sys
import json
import asyncio

# Ensure project root is on sys.path for module imports
sys.path.insert(0, os.path.abspath(os.getcwd()))

from tools.registry import ToolRegistry


def print_schema(tool):
    print(f"\n== {tool.get_name()} ==")
    desc = tool.get_description()
    print("Description:", desc)
    try:
        schema = tool.get_input_schema()
        schema_txt = json.dumps(schema, indent=2)
        print("Schema (full):")
        print(schema_txt)
    except Exception as e:
        print("Schema unavailable:", e)


async def main():
    reg = ToolRegistry()
    reg.build_tools()

    try:
        names = sorted(reg.list_descriptors().keys())
        print("Available tools (count=", len(names), "):")
        print(", ".join(names))
    except Exception as e:
        print("Listing tools failed:", e)

    # Show schemas for key tools
    for name in ["chat", "analyze", "codereview", "thinkdeep", "orchestrate_auto"]:
        # Add a clear separator line for readability in terminal
        print("\n" + "="*80)
        try:
            tool = reg.get_tool(name)
            print_schema(tool)
        except Exception as e:
            print(f"\n== {name} ==\nUnavailable:", e)

    # OrchestrateAuto dry run (no external calls)
    try:
        oa = reg.get_tool("orchestrate_auto")
        res = await oa.execute({
            "user_prompt": "Quick architecture survey of this repo",
            "dry_run": True,
            "step_budget": 2,
            "relevant_files": [os.path.abspath(os.path.join(os.getcwd(), "tools", "registry.py"))],
        })
        print("\n-- orchestrate_auto (dry_run) --")
        first = res[0]
        text = first.get("text") if isinstance(first, dict) else getattr(first, "text", "")
        print(text)
    except Exception as e:
        print("orchestrate_auto (dry_run) failed:", e)

    # Analyze step 1 minimal (no expert external call)
    try:
        an = reg.get_tool("analyze")
        sample_file = os.path.abspath(os.path.join(os.getcwd(), "tools", "chat.py"))
        args = {
            "model": os.getenv("ORCHESTRATOR_DEFAULT_MODEL", "glm-4.5-flash"),
            "step": "Start analysis: outline plan and targets",
            "step_number": 1,
            "total_steps": 1,
            "next_step_required": False,
            "findings": "Planning initial investigation",
            "relevant_files": [sample_file] if os.path.exists(sample_file) else [],
            "files_checked": [],
            "use_assistant_model": False,
        }
        res = await an.execute(args)
        print("\n-- analyze (step 1) --")
        first = res[0]
        text = first.get("text") if isinstance(first, dict) else getattr(first, "text", "")
        print("\n".join((text or "").splitlines()[:30]))
    except Exception as e:
        print("analyze (step 1) failed:", e)


if __name__ == "__main__":
    asyncio.run(main())

