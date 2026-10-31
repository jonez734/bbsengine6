"""The skel/ module template matches the module contract that module.check enforces.

The template uses a bare ``import lib`` (its documented convention: it is copied into a new package,
where ``lib`` is a sibling). These tests copy it into a temporary package the same way, then load it,
so the check runs against the same layout a generated module gets.
"""

import importlib
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from bbsengine6 import module

SKEL = Path(__file__).resolve().parents[1] / "src" / "skel"


@pytest.fixture
def generated_package(tmp_path, monkeypatch):
    """Copy skel/ into a fresh package named ``newmod`` and import it, as a generator would."""
    root = tmp_path / "pkgroot"
    pkg = root / "newmod"
    pkg.mkdir(parents=True)
    # copy contents only: copytree also copies metadata (copystat), which some sandboxes forbid
    for src in SKEL.glob("*.py"):
        shutil.copyfile(src, pkg / src.name)
    monkeypatch.syspath_prepend(str(root))
    for name in list(sys.modules):
        if name == "newmod" or name.startswith("newmod."):
            del sys.modules[name]
    pkg_mod = importlib.import_module("newmod")
    yield pkg_mod
    for name in list(sys.modules):
        if name == "newmod" or name.startswith("newmod."):
            del sys.modules[name]


@pytest.mark.unit
def test_skel_init_callables_match_the_contract(generated_package):
    stubs = {
        "init": module._stub_init,
        "access": module._stub_access,
        "buildargs": module._stub_buildargs,
        "main": module._stub_main,
    }
    with patch.object(module.io, "echo"):
        for fn, stub in stubs.items():
            assert module._check_func_signature(getattr(generated_package, fn), stub, name=fn), fn


@pytest.mark.unit
def test_skel_help_matches_the_optional_contract(generated_package):
    assert callable(generated_package.help)
    with patch.object(module.io, "echo"):
        assert module._check_func_signature(generated_package.help, module._stub_help, name="help")


@pytest.mark.unit
def test_skel_main_module_callables_match_the_contract(generated_package):
    main_mod = importlib.import_module("newmod.main")
    stubs = {
        "init": module._stub_init,
        "access": module._stub_access,
        "buildargs": module._stub_buildargs,
        "main": module._stub_main,
    }
    with patch.object(module.io, "echo"):
        for fn, stub in stubs.items():
            assert module._check_func_signature(getattr(main_mod, fn), stub, name=f"main.{fn}"), fn


@pytest.mark.unit
def test_skel_checkmodule_passes_the_package_prefixed_name(generated_package):
    lib = importlib.import_module("newmod.lib")
    with patch.object(lib.module, "check", return_value=True) as check:
        assert lib.checkmodule(None, "main") is True
    # The prefix comes from PACKAGENAME, which a generator sets to the new package's name.
    assert check.call_args[0][1] == f"{lib.PACKAGENAME}.main"


@pytest.mark.unit
def test_skel_lib_does_not_import_the_removed_bbsengine_module():
    src = (SKEL / "lib.py").read_text()
    assert "bbsengine" not in src.replace("bbsengine6", ""), src
