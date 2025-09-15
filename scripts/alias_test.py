# DEPRECATION NOTICE
# Deprecated developer sandbox. Prefer EXAI MCP routes.
# See docs/sweep_reports/current_exai_reviews/scripts_sweep_2025-09-15.md


#!/usr/bin/env python3
import os, sys, asyncio
sys.path.insert(0, '.')

os.environ.setdefault('STREAM_PROGRESS','true')
os.environ.setdefault('AUGGIE_CLI','true')
os.environ.setdefault('LOG_LEVEL','INFO')
os.environ.setdefault('LOG_FORMAT','plain')

import server

async def main():
    args = {"step":"Alias test","step_number":1,"total_steps":1,"next_step_required":False,"findings":"demo"}
    res = await server.handle_call_tool('planner_exai', args)
    print('OK: returned', len(res), 'items')
    for item in res:
        print(getattr(item,'text',str(item))[:300])

if __name__ == '__main__':
    asyncio.run(main())

