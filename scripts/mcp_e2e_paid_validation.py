# Back-compat shim: forwards to canonical subfolder
if __name__ == "__main__":
    import pathlib, runpy, sys
    target = pathlib.Path(__file__).parent / "e2e" / "mcp_e2e_paid_validation.py"
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
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
import mcp.types as types

PROJECT_DIR = Path(__file__).parent
WRAPPER = str(PROJECT_DIR / 'mcp_server_wrapper.py')


def pick_python():
    # Prefer py -3 on Windows if present and works, else fallback to python
    import shutil
    py = shutil.which('py')
    if py:
        return py, ['-3', '-u', WRAPPER]
    pyexe = shutil.which('python')
    if pyexe:
        return pyexe, ['-u', WRAPPER]
    # Last resort: current interpreter
    return os.sys.executable, [WRAPPER]


async def run_paid_validation():
    cmd, args = pick_python()
    params = StdioServerParameters(
        command=cmd,
        args=args,
        cwd=str(PROJECT_DIR),
        env={
            'PYTHONPATH': str(PROJECT_DIR),
            'LOG_LEVEL': os.getenv('LOG_LEVEL','INFO'),
            'GLM_API_KEY': os.getenv('GLM_API_KEY',''),
            'GLM_API_URL': os.getenv('GLM_API_URL','https://api.z.ai/api/paas/v4'),
            'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL','auto'),
        }
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"Initialized server: {init.serverInfo.name} {init.serverInfo.version}")
            tools = await session.list_tools()
            print('TOOLS AVAILABLE:', sorted([t.name for t in tools.tools]))

            # 1) chat: glm-4.5-air
            chat_args = {
                'model': 'glm-4.5-air',
                'prompt': 'Answer 1+1 as a number only.',
                'thinking_mode': 'minimal',
                'use_websearch': False,
            }
            print("\n— Running chat (glm-4.5-air)")
            try:
                chat_res = await session.call_tool('chat', arguments=chat_args)
                chat_texts = [c.text for c in chat_res.content if isinstance(c, types.TextContent)]
                chat_out = "\n".join(chat_texts)
                print("Tool: chat\nPrompt:", chat_args['prompt'])
                print("Model:", chat_args['model'])
                print("Output:")
                print(chat_out)
            except Exception as e:
                print("chat failed:", e)

            # 2) consensus: glm-4.5-air, step 1 only
            cons_args = {
                'step': 'Answer 1+1 as a number only.',
                'step_number': 1,
                'total_steps': 1,
                'next_step_required': False,
                'findings': 'Independent analysis: expecting a numeric string only.',
                'models': [ {'model': 'glm-4.5-air'} ],
                'model': 'glm-4.5-air',
            }
            print("\n— Running consensus (glm-4.5-air)")
            try:
                cons_res = await session.call_tool('consensus', arguments=cons_args)
                cons_texts = [c.text for c in cons_res.content if isinstance(c, types.TextContent)]
                cons_out = "\n".join(cons_texts)
                print("Tool: consensus\nPrompt:", cons_args['step'])
                print("Model:", 'glm-4.5-air')
                print("Output:")
                print(cons_out)
            except Exception as e:
                print("consensus failed:", e)


if __name__ == '__main__':
    asyncio.run(run_paid_validation())

