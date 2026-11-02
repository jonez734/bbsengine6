"""Mask secret values before they are printed to a log or debug echo.

No imports from the rest of bbsengine6, so any module (database, member, console) can use it without a
cycle. ``redact`` returns a copy; the caller's object is never changed.
"""

from __future__ import annotations

from typing import Any

# Keys whose values must never reach a log or debug echo.
SECRET_KEYS = frozenset({"password", "passwd", "passwordhash", "password_hash"})


def redact(value: Any) -> Any:
    """A copy of ``value`` safe to print: secret keys are masked, nested dicts and lists are redacted."""
    if isinstance(value, dict):
        return {k: ("***" if str(k).lower() in SECRET_KEYS else redact(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(redact(v) for v in value)
    return value
