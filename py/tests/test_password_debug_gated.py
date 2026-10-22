"""Password-related debug echoes run only when debugging is on.

A debug echo that mentions a password must sit under a debug guard, so a
normal login or password set prints nothing about it. The echo must not print
a password value even when debugging.
"""

import pathlib
import re

import bbsengine6

SRC = pathlib.Path(bbsengine6.__file__).parent

PASSWORD_DEBUG = re.compile(r"level=\"debug\"")
PW_WORD = re.compile(r"password", re.IGNORECASE)
GUARD = re.compile(r"if\s+.*(?:\bdebug\b|_PASSWORD_DEBUG)")


def _unguarded_password_debug(path: pathlib.Path):
    lines = path.read_text().splitlines()
    out = []
    for i, line in enumerate(lines):
        if not (PASSWORD_DEBUG.search(line) and PW_WORD.search(line)):
            continue
        # Look back a few lines for an `if ... debug` guard at a shallower indent.
        indent = len(line) - len(line.lstrip())
        guarded = False
        for j in range(i - 1, max(-1, i - 6), -1):
            prev = lines[j]
            if not prev.strip():
                continue
            if len(prev) - len(prev.lstrip()) < indent and GUARD.search(prev):
                guarded = True
            break
        if not guarded:
            out.append(f"{path}:{i + 1}: {line.strip()}")
    return out


def test_password_debug_echoes_are_gated():
    offenders = []
    for name in ("util.py", "member/lib.py"):
        offenders += _unguarded_password_debug(SRC / name)
    assert offenders == [], "\n".join(offenders)
