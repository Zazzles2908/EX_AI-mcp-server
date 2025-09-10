import os, sys, asyncio, json
# Ensure project root is on sys.path when running from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from server import handle_call_tool

# Configure environment for web mode and auto-continue (small)
os.environ.setdefault('CLAUDE_DEFAULTS_USE_WEBSEARCH', 'true')
os.environ.setdefault('EX_AUTOCONTINUE_WORKFLOWS', 'true')
os.environ.setdefault('EX_AUTOCONTINUE_ONLY_THINKDEEP', 'true')
os.environ.setdefault('EX_AUTOCONTINUE_MAX_STEPS', '2')

async def main():
    args = {
        'step': (
            'Use provider-native web browsing to find current context windows and model aliases for: '
            'Moonshot/Kimi and ZhipuAI GLM. Focus on >=128k, 200k, 256k context and API enablement steps. '
            'Output: short bullet summary + exact model names/aliases/provider, and note any requirements to enable long context.'
        ),
        'step_number': 1,
        'total_steps': 2,
        'next_step_required': True,
        'findings': 'Plan web queries.',
        'model': 'auto',
        'use_websearch': True,
        'thinking_mode': 'medium'
    }
    res = await handle_call_tool('thinkdeep', args)
    # Print the last text content block
    for i, item in enumerate(res):
        text = getattr(item, 'text', None)
        if text:
            print(f"\n=== BLOCK {i} ===\n{text[:4000]}\n")

if __name__ == '__main__':
    asyncio.run(main())

