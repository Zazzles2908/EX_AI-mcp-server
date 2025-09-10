import asyncio
import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession
from mcp.types import TextContent

PROJECT_DIR = Path(__file__).resolve().parent.parent
WRAPPER = str(PROJECT_DIR / 'scripts' / 'mcp_server_wrapper.py')
README = str(PROJECT_DIR / 'README.md')


# Overrides for specific tools to improve validity of requests
WORKFLOW_OVERRIDES = {
    "codereview": {
        "relevant_files": [str((PROJECT_DIR / 'server.py').resolve())],
        "findings": "Review server.py for code quality, security pitfalls, and maintainability concerns.",
        "step": "Initial review scope and plan"
    },
    "refactor": {
        "relevant_files": [str((PROJECT_DIR / 'server.py').resolve())],
        "findings": "Identify decomposition and readability improvements in server.py; focus on smaller functions and clearer boundaries.",
        "step": "Initial refactor assessment"
    },
    "secaudit": {
        "relevant_files": [str((PROJECT_DIR / 'server.py').resolve())],
        "findings": "Audit server.py against OWASP Top 10; focus on input validation, secrets handling, and dependency risks.",
        "step": "Initial threat modeling and scope definition"
    },
}


def build_args_from_schema(schema: dict, tool_name: str | None = None) -> dict:
    """Construct minimal valid arguments based on the provided JSON schema."""
    if not schema:
        return {}
    props = schema.get('properties', {}) or {}
    required = schema.get('required', []) or []

    args: dict = {}

    # Helper defaults
    def default_for(prop_schema: dict, name: str):
        t = prop_schema.get('type')
        if isinstance(t, list):
            # pick the first type
            t = t[0] if t else None
        if t == 'string':
            # Provide specifics for common fields
            if name in {'step', 'findings'}:
                return 'Automated test step'
            if name == 'step_number':
                return 1
            if name == 'total_steps':
                return 1
            if name == 'target_description':
                return 'Trace minimal target for test'
            if name == 'server_name':
                return 'test'
            if name == 'prompt':
                return 'Hello from MCP tool sweep test.'
            if name == 'model':
                return 'auto'
            return 'test'
        if t == 'number' or t == 'integer':
            if name == 'step_number' or name == 'total_steps':
                return 1
            return 1
        if t == 'boolean':
            if name == 'next_step_required':
                return False
            return True
        if t == 'array':
            items = prop_schema.get('items', {})
            item_type = items.get('type')
            if item_type == 'string':
                # Provide a real file path when possible
                if name in {'files', 'files_checked', 'relevant_files'}:
                    return [README]
                return ['a']
            return []
        if t == 'object':
            return {}
        # Fallback
        return 'test'

    for name, p in props.items():
        if name in required or name in {'step', 'step_number', 'total_steps', 'next_step_required', 'findings'}:
            args[name] = default_for(p, name)

    # Apply workflow overrides when appropriate
    tn = (tool_name or '').lower()
    if tn in WORKFLOW_OVERRIDES:
        for k, v in WORKFLOW_OVERRIDES[tn].items():
            if k in props:
                args[k] = v

    # Heuristics for known workflow tools
    for k in ['step', 'findings', 'step_number', 'total_steps', 'next_step_required']:
        if k in props and k not in args:
            args[k] = default_for(props[k], k)

    # Provide relevant_files when present
    if 'relevant_files' in props and not args.get('relevant_files'):
        args['relevant_files'] = [README]

    # Docgen counters sanity (allow completion when zero)
    if 'total_files_to_document' in props and 'num_files_documented' in props:
        args.setdefault('total_files_to_document', 0)
        args.setdefault('num_files_documented', 0)
        # If tool requires next step, set false to finish
        if 'next_step_required' in props:
            args['next_step_required'] = False

    # Prefer to skip expert model calls in sweep to prevent long timeouts
    if 'use_assistant_model' in props and 'use_assistant_model' not in args:
        args['use_assistant_model'] = False

    # Precommit defaults
    if 'path' in props and 'compare_to' in props:
        args.setdefault('path', str(PROJECT_DIR))

    # For tools expecting 'trace_mode' and 'target_description'
    if 'trace_mode' in props and 'target_description' in props:
        # Force to 'ask' to avoid validation errors and to let tool decide next
        args['trace_mode'] = 'ask'
        args.setdefault('target_description', 'Test tracing target')

    # Always try to supply model when accepted
    if 'model' in props and 'model' not in args:
        args['model'] = 'auto'

    return args


_SUM_LINES: list[dict] = []

async def run_sweep():
    print('# MCP Tool Sweep Report')
    print()
    env = {
        **os.environ,
        'PYTHONPATH': str(PROJECT_DIR),
        'ENV_FILE': str(PROJECT_DIR / '.env'),
        'LOG_LEVEL': os.getenv('LOG_LEVEL', 'ERROR'),
        'STREAM_PROGRESS': 'false',
    }

    params = StdioServerParameters(
        command=str(PROJECT_DIR / '.venv' / 'Scripts' / 'python.exe'),
        args=['-u', WRAPPER],
        cwd=str(PROJECT_DIR),
        env=env,
    )
    # Print key env for debugging
    print(f"- Using DEFAULT_MODEL={env.get('DEFAULT_MODEL')}")
    print(f"- Providers: KIMI={'set' if env.get('KIMI_API_KEY') else 'unset'}, GLM={'set' if env.get('GLM_API_KEY') else 'unset'}")

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await asyncio.wait_for(session.initialize(), timeout=20)
                print(f"- Initialized server: {init.serverInfo.name} v{init.serverInfo.version}")
                tools = await asyncio.wait_for(session.list_tools(), timeout=20)
                names = [t.name for t in tools.tools]
                print(f"- Tools discovered ({len(names)}): {', '.join(sorted(names))}")
                print()

                # Build a lookup of schemas
                schemas = {}
                for t in tools.tools:
                    schema = getattr(t, 'inputSchema', None) or getattr(t, 'input_schema', None)
                    if isinstance(schema, dict):
                        schemas[t.name] = schema

                # Helper: categorize workflow tools and set per-tool timeout
                workflow_tools = {'codereview', 'refactor', 'secaudit'}

                # Ensure env allows these tools (override CLAUDE_* lists in this context)
                try:
                    os.environ.pop('CLAUDE_TOOL_DENYLIST', None)
                    os.environ.pop('CLAUDE_TOOL_ALLOWLIST', None)
                except Exception:
                    pass

                # Iterate tools
                for name in sorted(names):
                    schema = schemas.get(name, {})
                    args = build_args_from_schema(schema, tool_name=name)

                    print(f"## Tool: {name}")
                    if schema:
                        print("<details><summary>Input Schema</summary>")
                        print()
                        print("```json")
                        print(json.dumps(schema, indent=2))
                        print("```")
                        print("</details>")
                    print()
                    print("Request:")
                    print("```json")
                    print(json.dumps(args, indent=2))
                    print("```")

                    try:
                        # Adjust timeout for workflow tools
                        timeout = 90 if name in workflow_tools else 45
                        import time as _time
                        _start = _time.time()
                        res = await asyncio.wait_for(session.call_tool(name, arguments=args), timeout=timeout)
                        duration = _time.time() - _start
                        texts = [c.text for c in res.content if isinstance(c, TextContent)]
                        raw = ("\n\n".join(texts)).strip() if texts else ""

                        # Attempt to parse a ToolOutput JSON payload from the model text
                        parsed = None
                        display = raw
                        try:
                            if raw:
                                # If output contains multiple JSON blocks, pick the first valid
                                # Simple heuristic: find first '{' and try to json.loads
                                first_brace = raw.find('{')
                                if first_brace != -1:
                                    candidate = raw[first_brace:]
                                    parsed = json.loads(candidate)
                        except Exception:
                            parsed = None

                        # Prefer parsed content for provider/model metadata and error messages
                        provider = None
                        model_used = None
                        status = None
                        content = None
                        if isinstance(parsed, dict):
                            provider = (parsed.get('metadata') or {}).get('provider_used') or parsed.get('provider_used')
                            model_used = (parsed.get('metadata') or {}).get('model_used') or parsed.get('model_used')
                            status = parsed.get('status')
                            content = parsed.get('content')
                            # Choose the most informative text to show
                            if content:
                                display = content
                            elif raw:
                                display = raw
                        else:
                            display = raw or "<no text content>"

                        # Limit very long outputs
                        preview = display if len(display) < 4000 else display[:4000] + "\n...\n[truncated]"
                        print()
                        # Success if status not error
                        is_error = (status == 'error')
                        print("Result: ERROR" if is_error else "Result: SUCCESS")
                        if provider or model_used:
                            print()
                            print(f"Resolved: provider={provider or 'unknown'}, model={model_used or 'unknown'}")
                        print(f"- Duration: {duration:.2f}s")
                        print()
                        print("```text")
                        print(preview)
                        print("```")
                        # Append to summary line file for perf tracking
                        try:
                            _summary = {
                                'tool': name, 'status': 'error' if is_error else 'success',
                                'provider': provider or None, 'model': model_used or None,
                                'duration_sec': round(duration, 2)
                            }
                            _SUM_LINES.append(_summary)
                        except Exception:
                            pass
                    except Exception as e:
                        print()
                        print("Result: ERROR")
                        print()
                        print("```text")
                        # Include class name and message for debugging
                        print(f"{e.__class__.__name__}: {e}")
                        print("```")
                        try:
                            _SUM_LINES.append({'tool': name, 'status': 'error', 'error': str(e)})
                        except Exception:
                            pass

                    print()

    except Exception as e:
        print("\nFATAL: Could not initialize or run sweep:")
        print(str(e))


if __name__ == '__main__':
    import contextlib, io, sys
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        asyncio.run(run_sweep())
    content = buf.getvalue()

    # Legacy single-file report (backward compatible)
    legacy_path = PROJECT_DIR / 'docs' / 'mcp_tool_sweep_report.md'
    try:
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    legacy_path.write_text(content, encoding='utf-8')

    # Timestamped report under docs/sweep_reports/YYYY-MM-DD_HH-MM-SS/
    from datetime import datetime
    ts = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    ts_dir = PROJECT_DIR / 'docs' / 'sweep_reports' / ts
    ts_dir.mkdir(parents=True, exist_ok=True)
    ts_path = ts_dir / 'mcp_tool_sweep_report.md'
    ts_path.write_text(content, encoding='utf-8')

    # Write minimal metadata and summary
    import subprocess
    try:
        commit = subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=str(PROJECT_DIR), text=True).strip()
    except Exception:
        commit = None
    meta = {
        'timestamp': ts,
        'default_model': os.getenv('DEFAULT_MODEL'),
        'providers': {
            'GLM_API_KEY': bool(os.getenv('GLM_API_KEY')),
            'KIMI_API_KEY': bool(os.getenv('KIMI_API_KEY')),
            'OPENROUTER_API_KEY': bool(os.getenv('OPENROUTER_API_KEY')),
        },
        'git_commit': commit,
        'summary': _SUM_LINES,
    }
    (ts_dir / 'metadata.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
    (ts_dir / 'summary.jsonl').write_text("\n".join(json.dumps(x) for x in _SUM_LINES), encoding='utf-8')

    print(f"Wrote report to {legacy_path}")
    print(f"Wrote timestamped report to {ts_path}")

