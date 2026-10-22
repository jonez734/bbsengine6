"""No bbsengine6 module calls the removed member.getcurrentid or member.getbyid."""

import ast
from pathlib import Path

import bbsengine6

SRC = Path(bbsengine6.__file__).parent
REMOVED = {"getcurrentid", "getbyid"}


def _calls_removed(path: Path):
    tree = ast.parse(path.read_text())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
            if name in REMOVED:
                out.append(f"{path.relative_to(SRC)}:{node.lineno}: {name}()")
    return out


def test_no_bbsengine6_module_calls_removed_member_functions():
    offenders = []
    for p in SRC.rglob("*.py"):
        if "member" in p.parts and p.name == "lib.py":
            # The definitions themselves (raise stubs) live here.
            continue
        offenders += _calls_removed(p)
    assert offenders == [], "\n".join(offenders)
