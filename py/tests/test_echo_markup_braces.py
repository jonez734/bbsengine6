"""io.echo markup must use single braces ({var:...}) in plain strings.

A plain string with doubled braces ({{var:...}}) is not unescaped, and the echo engine
renders nothing for it: the message is silently swallowed. Doubled braces are only correct
inside an f-string, where they become single braces before echo sees them.
"""

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "bbsengine6"

# Calls whose first argument is printed or used as a prompt, so markup in it is rendered.
ECHO_FUNCS = {"echo", "echo_traceback", "inputstring", "inputboolean", "inputchoice",
              "inputinteger", "inputpassword"}


def _plain_string_echo_calls():
    """(file, line, text) for io.echo calls whose first argument is a non-f-string literal
    containing doubled braces."""
    hits = []
    for f in SRC.rglob("*.py"):
        if "tests" in f.parts:
            continue
        try:
            tree = ast.parse(f.read_text())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
            if name not in ECHO_FUNCS or not node.args:
                continue
            arg = node.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if "{{" in arg.value or "}}" in arg.value:
                    hits.append((str(f.relative_to(SRC)), node.lineno, arg.value[:60]))
    return hits


@pytest.mark.unit
def test_no_plain_echo_string_uses_doubled_braces():
    hits = _plain_string_echo_calls()
    assert hits == [], "doubled braces in a plain io.echo string are swallowed:\n" + "\n".join(
        f"  {f}:{ln}: {t!r}" for f, ln, t in hits
    )
