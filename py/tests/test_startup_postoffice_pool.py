"""bbsengine6 startup hands postoffice a pool.

Regression: postoffice.startup_main returns False ("pool is None") when called
with neither conn nor pool, and bed startup then failed. The call must pass the
same target pool the stage_one step uses.
"""

import importlib
import inspect
import pathlib

import pytest

startup_main = importlib.import_module("bbsengine6.startup.main")


@pytest.mark.unit
def test_postoffice_call_passes_target_pool():
    src = inspect.getsource(startup_main.main)
    call = [line for line in src.splitlines() if 'package="postoffice"' in line]
    assert call, "postoffice runmodule call not found"
    assert "pool=target_pool" in call[0]


@pytest.mark.unit
def test_os_is_imported_where_the_diagnostic_uses_it():
    """The pre-flight diagnostic reads os.environ; the module must import os."""
    import ast

    tree = ast.parse(pathlib.Path(startup_main.__file__).read_text(encoding="utf-8"))
    imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    used = any(isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == "os"
               for n in ast.walk(tree))
    assert (not used) or ("os" in imported), "startup/main.py uses os without importing it"
