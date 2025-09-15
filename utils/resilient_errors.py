"""
Resilient error handling primitives (skeleton)

Provides lightweight retry/backoff wrappers and a standard error mapping so tool
implementations can surface concise, actionable messages while logs retain detail.

Environment knobs:
- RESILIENT_RETRIES=2 (default)
- RESILIENT_BACKOFF_SECS=1.5 (default)
"""
from __future__ import annotations

import time
from typing import Callable, Tuple, Type


def _get_env_float(name: str, default: float) -> float:
    import os
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def with_retries(fn: Callable[[], Tuple[bool, str]], *, retries: int | None = None, backoff_secs: float | None = None) -> Tuple[bool, str]:
    """
    Execute fn() -> (ok, message) with simple retries and backoff.
    """
    if retries is None:
        retries = int(_get_env_float("RESILIENT_RETRIES", 2))
    if backoff_secs is None:
        backoff_secs = _get_env_float("RESILIENT_BACKOFF_SECS", 1.5)

    attempt = 0
    last_msg = ""
    while attempt <= retries:
        ok, msg = fn()
        if ok:
            return True, msg
        last_msg = msg
        if attempt == retries:
            break
        time.sleep(backoff_secs)
        attempt += 1
    return False, last_msg


class ErrorCategory:
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    INPUT = "input"
    UNKNOWN = "unknown"


def categorize_error(exc: Exception) -> str:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    if "rate limit" in msg or "too many requests" in msg or "429" in msg:
        return ErrorCategory.RATE_LIMIT
    if "timeout" in msg or "timed out" in msg or "connection" in msg:
        return ErrorCategory.NETWORK
    if "unauthorized" in msg or "forbidden" in msg or "invalid api key" in msg:
        return ErrorCategory.AUTH
    if "invalid" in msg or "not found" in msg or "valueerror" in name:
        return ErrorCategory.INPUT
    return ErrorCategory.UNKNOWN


def user_friendly_message(exc: Exception) -> str:
    cat = categorize_error(exc)
    if cat == ErrorCategory.RATE_LIMIT:
        return "Provider rate limit hit. Please retry shortly or reduce request size."
    if cat == ErrorCategory.NETWORK:
        return "Network issue contacting provider. Check connectivity and retry."
    if cat == ErrorCategory.AUTH:
        return "Authentication issue with provider. Verify API key configuration."
    if cat == ErrorCategory.INPUT:
        return "Invalid input detected. Please correct arguments and try again."
    return "Unexpected error occurred. Please check server logs for details."

