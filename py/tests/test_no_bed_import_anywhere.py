"""No module under bbsengine6/ imports bed, at module level or lazily inside a function.

bbsengine6 must run without bed installed. Lazy imports are checked too, since an import inside a
function is still a dependency at call time.
"""

import ast
from pathlib import Path

import bbsengine6

PACKAGE = Path(bbsengine6.__file__).parent


def _bed_imports(path: Path):
    tree = ast.parse(path.read_text(), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "bed":
            found.append(f"from {node.module} (line {node.lineno})")
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] == "bed":
                    found.append(f"import {a.name} (line {node.lineno})")
    return found


def test_no_module_in_the_package_imports_bed():
    offenders = {}
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        hits = _bed_imports(path)
        if hits:
            offenders[str(path.relative_to(PACKAGE))] = hits
    assert offenders == {}, f"bbsengine6 must not import bed: {offenders}"
