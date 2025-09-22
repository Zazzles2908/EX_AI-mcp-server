import asyncio
import os
import shutil
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
    py = shutil.which('py')
    if py:
        return py, ['-3', '-u', WRAPPER]
    pyexe = shutil.which('python')
    if pyexe:
        return pyexe, ['-u', WRAPPER]
    # Last resort: current interpreter
    return os.sys.executable, [WRAPPER]


async def call_version(session: ClientSession):
    try:
        res = await session.call_tool('version', arguments={})
        texts = [c.text for c in res.content if isinstance(c, types.TextContent)]
        print("VERSION:", ("\n".join(texts))[:800])
    except Exception as e:
        print("VERSION call failed:", e)


async def call_listmodels(session: ClientSession):
    try:
        res = await session.call_tool('listmodels', arguments={})
        texts = [c.text for c in res.content if isinstance(c, types.TextContent)]
        print("LISTMODELS:", ("\n".join(texts))[:1200])
    except Exception as e:
        print("LISTMODELS call failed:", e)


async def call_chat(session: ClientSession):
    model = None
    if os.getenv('KIMI_API_KEY'):
        model = 'kimi-k2-0711-preview'
    elif os.getenv('GLM_API_KEY'):
        model = 'glm-4.5-air'  # prefer a known-allowed model per .env
    if not model:
        print('CHAT: skipped (no KIMI_API_KEY or GLM_API_KEY)')
        return
    try:
        args = {'model': model, 'prompt': 'Say hello in 1 short line.', 'thinking_mode': 'minimal'}
        res = await session.call_tool('chat', arguments=args)
        texts = [c.text for c in res.content if isinstance(c, types.TextContent)]
        print(f"CHAT[{model}]:", ("\n".join(texts))[:400])
    except Exception as e:
        print("CHAT call failed:", e)


async def main():
    cmd, args = pick_python()
    params = StdioServerParameters(
        command=cmd,
        args=args,
        cwd=str(PROJECT_DIR),
        env={
            'PYTHONPATH': str(PROJECT_DIR),
            'LOG_LEVEL': os.getenv('LOG_LEVEL','INFO'),
            'KIMI_API_KEY': os.getenv('KIMI_API_KEY',''),
            'KIMI_API_URL': os.getenv('KIMI_API_URL','https://api.moonshot.ai/v1'),
            'GLM_API_KEY': os.getenv('GLM_API_KEY',''),
            'GLM_API_URL': os.getenv('GLM_API_URL','https://api.z.ai/api/paas/v4'),
            'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL','auto'),
        }
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print('Initialized server:', init.serverInfo.name, init.serverInfo.version)
            tools = await session.list_tools()
            print('TOOLS AVAILABLE:', sorted([t.name for t in tools.tools]))

            await call_version(session)
            await call_listmodels(session)
            await call_chat(session)

if __name__ == '__main__':
    asyncio.run(main())

