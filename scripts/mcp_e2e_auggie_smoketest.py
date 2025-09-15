# DEPRECATION NOTICE
# This script is deprecated in favor of EXAI MCP routes for E2E validation.
# Use instead:
#  - Health: status_exai-mcp (hub=true)
#  - Quick QA: chat_exai-mcp on glm-4.5-flash
#  - Reviews/Reports: analyze_exai-mcp / codereview_exai-mcp / testgen_exai-mcp
# See docs/sweep_reports/current_exai_reviews/scripts_sweep_2025-09-15.md


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

async def list_tools(session: ClientSession):
    tools = await session.list_tools()
    names = sorted([t.name for t in tools.tools])
    print('TOOLS AVAILABLE:', names)
    return names

async def main():
    # Force Auggie exposure
    env = {
        'PYTHONPATH': str(PROJECT_DIR),
        'LOG_LEVEL': os.getenv('LOG_LEVEL','INFO'),
        'KIMI_API_KEY': os.getenv('KIMI_API_KEY',''),
        'KIMI_API_URL': os.getenv('KIMI_API_URL','https://api.moonshot.ai/v1'),
        'GLM_API_KEY': os.getenv('GLM_API_KEY',''),
        'GLM_API_URL': os.getenv('GLM_API_URL','https://api.z.ai/api/paas/v4'),
        'DEFAULT_MODEL': os.getenv('DEFAULT_MODEL','auto'),
        'ALLOW_AUGGIE': 'true',
        'AUGGIE_CLI': 'true',
    }

    import shutil, sys
cmd = shutil.which('py')
args = ['-3', '-u', WRAPPER] if cmd else None
if not cmd:
    cmd = shutil.which('python') or sys.executable
    args = ['-u', WRAPPER]
params = StdioServerParameters(command=cmd, args=args, cwd=str(PROJECT_DIR), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print('Initialized server:', init.serverInfo.name, init.serverInfo.version)
            names = await list_tools(session)

            assert 'aug_chat' in names and 'aug_thinkdeep' in names and 'aug_consensus' in names, 'Auggie aug_* tools not exposed'
            print('Auggie aug_* tools present: OK')

            # Quick aug_chat call
            try:
                args = {'prompt': 'Say hello briefly.', 'model': os.getenv('KIMI_DEFAULT_MODEL','kimi-k2-0711-preview')}
                res = await session.call_tool('aug_chat', arguments=args)
                texts = [c.text for c in res.content if isinstance(c, types.TextContent)]
                print('AUG_CHAT:', ("\n".join(texts))[:400])
            except Exception as e:
                print('AUG_CHAT call failed:', e)

if __name__ == '__main__':
    asyncio.run(main())

