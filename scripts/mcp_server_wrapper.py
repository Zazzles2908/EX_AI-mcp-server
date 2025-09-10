#!/usr/bin/env python3
"""
MCP Server Wrapper for auggie compatibility
This wrapper ensures environment variables are properly inherited and the server starts correctly
"""

import os
import sys
from pathlib import Path

# Robust autodiscovery: locate project root (ex-mcp-server), .venv, and server.py from any cwd
cur = Path(__file__).resolve()
# Try typical structure: scripts/ is under project root
project_dir = cur.parent.parent if cur.parent.name == 'scripts' else cur.parent
# Fallback: search upwards for server.py
if not (project_dir / 'server.py').exists():
    p = project_dir
    while p != p.parent:
        if (p / 'server.py').exists():
            project_dir = p
            break
        p = p.parent

# Ensure logs dir exists
(project_dir / 'logs').mkdir(exist_ok=True)

# Single-instance lock (PID file) to avoid duplicate servers
try:
    import time, atexit
    lock_dir = project_dir / 'logs'
    lock_path = lock_dir / 'exai_server.pid'
    disable_lock = os.getenv('EXAI_LOCK_DISABLE', 'false').strip().lower() in {'1','true','yes','on'}
    if not disable_lock:
        stale_sec = float(os.getenv('EXAI_LOCK_STALE_SECONDS', '900'))  # 15 minutes default
        pid_in_file: int | None = None
        if lock_path.exists():
            try:
                # Try PID-aware check first
                txt = (lock_path.read_text(encoding='utf-8').strip() or '')
                pid_in_file = int(txt) if txt.isdigit() else None
            except Exception:
                pid_in_file = None
            # If we found a PID, attempt to verify process existence
            pid_active = False
            if pid_in_file is not None:
                try:
                    try:
                        import psutil  # type: ignore
                        pid_active = psutil.pid_exists(pid_in_file)
                    except Exception:
                        # Fallback: mtime-based check if psutil not available
                        pid_active = False
                except Exception:
                    pid_active = False
            if pid_in_file is not None and pid_active:
                # Active PID holds the lock; refuse to start
                with open(lock_dir / 'wrapper_error.log', 'a', encoding='utf-8') as f:
                    f.write(f'Refusing to start: active EXAI MCP server appears to be running (pid={pid_in_file}). Set EXAI_LOCK_DISABLE=true to bypass.\n')
                sys.exit(1)
            else:
                # No active PID; check staleness window as final guard
                try:
                    mtime = lock_path.stat().st_mtime
                    if (time.time() - mtime) < stale_sec and pid_in_file is not None:
                        # Recently created but PID not found (e.g., race) — still refuse briefly to avoid flapping
                        with open(lock_dir / 'wrapper_error.log', 'a', encoding='utf-8') as f:
                            f.write(f'Refusing to start briefly: recent lock file with missing pid={pid_in_file}. Wait or set EXAI_LOCK_STALE_SECONDS lower.\n')
                        sys.exit(1)
                    else:
                        # Stale lock or no valid PID — remove and continue
                        lock_path.unlink(missing_ok=True)
                except Exception:
                    pass
        # Create lock and write PID
        with open(lock_path, 'w', encoding='utf-8') as lf:
            lf.write(str(os.getpid()))
        # Ensure cleanup on exit
        def _cleanup_lock():
            try:
                if lock_path.exists():
                    lock_path.unlink()
            except Exception:
                pass
        atexit.register(_cleanup_lock)
except Exception:
    # Never block startup due to lock errors
    pass


# Prefer venv python if available — auto re-exec to ensure deps are available to MCP clients
# This preserves stdio handles and environment; VS Code expects the server to start with all deps
venv_py = project_dir / '.venv' / 'Scripts' / 'python.exe'
if venv_py.exists() and sys.executable != str(venv_py):
    # preserve unbuffered mode for MCP stdio; keep same script path
    os.execv(str(venv_py), [str(venv_py), "-u", str(__file__)])

# Set working dir and sys.path
os.chdir(project_dir)
sys.path.insert(0, str(project_dir))
# Set Python path for child imports
os.environ.setdefault('PYTHONPATH', str(project_dir))
# Logging defaults: prefer INFO for CLI/streaming contexts unless explicitly overridden
if 'LOG_LEVEL' not in os.environ:
    if os.getenv('AUGGIE_CLI', '').strip().lower() == 'true' or os.getenv('STREAM_PROGRESS', 'true').strip().lower() == 'true':
        os.environ['LOG_LEVEL'] = 'INFO'
    else:
        os.environ['LOG_LEVEL'] = 'ERROR'

# Import and run the server
try:
    from server import run
except Exception as e:
    with open(project_dir / "logs" / "wrapper_error.log", "a", encoding="utf-8") as f:
        f.write(f"Wrapper import error: {e}\n")
    sys.exit(1)

if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        # Write error and ensure a non-zero exit so MCP client shows 'Server disconnected' with cause
        with open(project_dir / "logs" / "wrapper_error.log", "a", encoding="utf-8") as f:
            f.write(f"Wrapper run error: {e}\n")
        sys.exit(1)
