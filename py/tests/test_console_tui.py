"""bbsengine6.console.tui: the console TUI runs, routes subcommands, and is wired to the console script.

All tests are mocked: ``module.run`` and the interactive menu are patched, and no
database is touched. The ``python -m`` test runs ``--help``, which exits before
any database connection.
"""

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from bbsengine6.console import lib, tui

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src"


def _parse(argv):
    return tui.buildargs(None).parse_args(argv)


# --- contract -------------------------------------------------------------


@pytest.mark.unit
def test_tui_defines_the_callables_module_check_requires():
    for name in ("init", "buildargs", "access", "main"):
        assert callable(getattr(tui, name)), name


@pytest.mark.unit
def test_module_check_passes_for_tui():
    from bbsengine6 import module

    with patch.object(module.io, "echo"):
        assert module.check(None, "bbsengine6.console.tui") is True


@pytest.mark.unit
def test_access_and_init_return_true():
    assert tui.init(None) is True
    assert tui.access(None, "run") is True


# --- parser ---------------------------------------------------------------


@pytest.mark.unit
def test_buildargs_accepts_global_flags_before_the_subcommand():
    ns = _parse(["--debug", "--databasename", "zoid6x", "session"])
    assert ns.debug is True
    assert ns.databasename == "zoid6x"
    assert ns.subcommand == "session"
    assert ns.subargs == []


@pytest.mark.unit
def test_buildargs_passes_subcommand_words_through_unparsed():
    ns = _parse(["channel", "list", "--limit", "5"])
    assert ns.subcommand == "channel"
    assert ns.subargs == ["list", "--limit", "5"]


@pytest.mark.unit
def test_buildargs_with_no_subcommand_leaves_it_none():
    ns = _parse([])
    assert ns.subcommand is None
    assert ns.subargs == []


# --- routing --------------------------------------------------------------


@pytest.mark.unit
def test_console_subcommand_runs_through_module_run_with_its_argv():
    args = _parse(["session"])
    with patch.object(tui.module, "run", return_value=True) as run:
        assert tui.run_subcommand(args, "session", ["--x"]) is True
    run.assert_called_once()
    call_args, call_kwargs = run.call_args
    assert call_args[1] == "bbsengine6.console.session"
    assert call_kwargs["argv"] == ["--x"]


@pytest.mark.unit
def test_backend_subcommand_runs_from_the_backend_package():
    backend_name = sorted(lib.BACKEND_SUBCOMMANDS)[0]
    args = _parse([backend_name])
    with patch.object(tui.module, "run", return_value=True) as run:
        tui.run_subcommand(args, backend_name, [])
    _, kwargs = run.call_args
    assert kwargs["package"] == "bbsengine6.backend"
    assert run.call_args[0][1] == backend_name


@pytest.mark.unit
def test_unknown_subcommand_echoes_an_error_and_returns_false():
    args = _parse(["nosuch"])
    with patch.object(tui.module, "run") as run, patch.object(tui.io, "echo") as echo:
        assert tui.run_subcommand(args, "nosuch", []) is False
    run.assert_not_called()
    assert "Unknown subcommand: nosuch" in echo.call_args[0][0]


# --- main -----------------------------------------------------------------


@pytest.mark.unit
def test_main_with_no_subcommand_runs_the_interactive_menu():
    args = _parse([])
    with patch.object(tui, "run_menu", return_value=True) as menu, \
         patch.object(tui, "run_subcommand") as sub, \
         patch.object(tui.io, "echo"):
        rc = tui.main(args)
    menu.assert_called_once()
    sub.assert_not_called()
    assert rc is True


@pytest.mark.unit
def test_main_with_a_subcommand_does_not_open_the_menu():
    args = _parse(["session"])
    with patch.object(tui, "run_menu") as menu, \
         patch.object(tui, "run_subcommand", return_value=True) as sub, \
         patch.object(tui.io, "echo"):
        rc = tui.main(args)
    menu.assert_not_called()
    sub.assert_called_once()
    assert rc is True


@pytest.mark.unit
def test_main_returns_false_when_the_subcommand_fails():
    args = _parse(["session"])
    with patch.object(tui, "run_subcommand", return_value=False), \
         patch.object(tui.io, "echo"):
        assert tui.main(args) is False


@pytest.mark.unit
def test_cli_maps_failure_to_exit_code_1():
    with patch.object(tui, "main", return_value=False), \
         patch("bbsengine6.bottombar.init"), \
         patch.object(tui.lib, "setbottombar"), \
         patch.object(tui.io, "echo"):
        assert tui.cli([]) == 1


@pytest.mark.unit
def test_cli_maps_success_to_exit_code_0():
    with patch.object(tui, "main", return_value=True), \
         patch("bbsengine6.bottombar.init"), \
         patch.object(tui.lib, "setbottombar"), \
         patch.object(tui.io, "echo"):
        assert tui.cli([]) == 0


@pytest.mark.unit
def test_cursor_restore_is_skipped_on_a_non_tty():
    """Writing cursor escapes to a pipe raises in io.echo; the guard must skip them."""
    with patch.object(tui.sys.stdout, "isatty", return_value=False), \
         patch.object(tui.io, "echo") as echo:
        tui._restore_cursor()
    echo.assert_not_called()


@pytest.mark.unit
def test_cursor_restore_writes_on_a_tty():
    with patch.object(tui.sys.stdout, "isatty", return_value=True), \
         patch.object(tui.io, "echo") as echo:
        tui._restore_cursor()
    echo.assert_called_once()


@pytest.mark.unit
def test_main_handles_ctrl_c_without_raising():
    args = _parse([])
    with patch.object(tui, "run_menu", side_effect=KeyboardInterrupt), \
         patch.object(tui.io, "echo") as echo:
        assert tui.main(args) is True
    assert any("**INTR**" in str(c.args[0]) for c in echo.call_args_list)


@pytest.mark.unit
def test_main_handles_eof_without_raising():
    args = _parse([])
    with patch.object(tui, "run_menu", side_effect=EOFError), \
         patch.object(tui.io, "echo") as echo:
        assert tui.main(args) is True
    assert any("**EOF**" in str(c.args[0]) for c in echo.call_args_list)


# --- delegation and launch paths -----------------------------------------


@pytest.mark.unit
def test_dunder_main_delegates_to_tui_main():
    """console/__main__.py must call tui.cli, so the two entry points cannot drift."""
    import ast

    src = (PACKAGE_ROOT / "bbsengine6" / "console" / "__main__.py").read_text()
    tree = ast.parse(src)
    calls = [
        ast.unparse(node.func)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]
    assert "tui.cli" in calls, calls


@pytest.mark.unit
def test_console_script_target_resolves_to_tui_cli():
    """The [project.scripts] console entry names bbsengine6.console.tui:cli."""
    import tomllib

    data = tomllib.loads((PACKAGE_ROOT.parent / "pyproject.toml").read_text())
    target = data["project"]["scripts"]["console"]
    assert target == "bbsengine6.console.tui:cli"
    mod_name, func_name = target.split(":")
    assert getattr(importlib.import_module(mod_name), func_name) is tui.cli


@pytest.mark.unit
def test_tui_has_no_undefined_names():
    """An undefined name (for example a missing ``Optional`` import) breaks the installed
    package at import time. A static check on the source catches it here.
    """
    pyflakes_api = pytest.importorskip("pyflakes.api")
    from pyflakes.reporter import Reporter
    import io as _io

    out = _io.StringIO()
    pyflakes_api.checkPath(
        str(PACKAGE_ROOT / "bbsengine6" / "console" / "tui.py"),
        Reporter(out, out),
    )
    undefined = [line for line in out.getvalue().splitlines() if "undefined name" in line]
    assert not undefined, undefined


@pytest.mark.unit
def test_python_m_tui_help_lists_the_subcommands():
    env = dict(os.environ, PYTHONPATH=str(PACKAGE_ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "bbsengine6.console.tui", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "usage: console" in proc.stdout
    assert "{subcommand}" in proc.stdout or "[subcommand]" in proc.stdout
    assert "--debug" in proc.stdout
