"""Optional help(): module.run uses a module's own help() for --help, and module.check validates it.

Mocked throughout: the target is a stand-in module object, so no database or real command runs.
"""

import argparse
import types
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import module


def _target(**extra):
    """A minimal module object that passes the required contract for module.run's --help path."""
    ns = types.SimpleNamespace(
        init=MagicMock(return_value=True),
        access=MagicMock(return_value=True),
        buildargs=MagicMock(return_value=argparse.ArgumentParser("demo")),
        main=MagicMock(return_value=True),
    )
    for k, v in extra.items():
        setattr(ns, k, v)
    return ns


def _run_help(target, argv=("--help",)):
    with patch.object(module, "get", return_value=target), \
         patch.object(module, "check", return_value=True), \
         patch.object(module, "runcallback", side_effect=lambda a, cb, **kw: cb(a, **kw)), \
         patch.object(module.io, "echo"):
        return module.run(types.SimpleNamespace(debug=False), "demo", argv=list(argv))


@pytest.mark.unit
def test_help_method_is_used_for_help_and_buildargs_is_not_called():
    help_fn = MagicMock(return_value=None)
    target = _target(help=help_fn)
    rc = _run_help(target)
    assert rc is True
    help_fn.assert_called_once()
    target.buildargs.assert_not_called()


@pytest.mark.unit
def test_help_method_receives_the_run_kwargs():
    help_fn = MagicMock(return_value=None)
    target = _target(help=help_fn)
    with patch.object(module, "get", return_value=target), \
         patch.object(module, "check", return_value=True), \
         patch.object(module, "runcallback", side_effect=lambda a, cb, **kw: cb(a, **kw)), \
         patch.object(module.io, "echo"):
        module.run(types.SimpleNamespace(debug=False), "demo", argv=["-h"], pool="P")
    _, kwargs = help_fn.call_args
    assert kwargs.get("pool") == "P"


@pytest.mark.unit
def test_without_help_method_buildargs_still_prints_its_help():
    target = _target()
    parser = MagicMock()
    target.buildargs = MagicMock(return_value=parser)
    rc = _run_help(target)
    assert rc is True
    target.buildargs.assert_called()
    parser.print_help.assert_called_once()


@pytest.mark.unit
def test_check_accepts_a_help_with_the_contract_signature():
    def help(**kwargs) -> None:
        return None

    with patch.object(module.io, "echo"):
        ok = module._check_func_signature(help, module._stub_help)
    assert ok is True


@pytest.mark.unit
def test_check_rejects_a_help_with_a_positional_args_parameter():
    def help(args, **kwargs) -> None:
        return None

    with patch.object(module.io, "echo"):
        ok = module._check_func_signature(help, module._stub_help)
    assert ok is False


@pytest.mark.unit
def test_check_rejects_a_help_that_returns_a_value():
    def help(**kwargs) -> bool:
        return True

    with patch.object(module.io, "echo"):
        ok = module._check_func_signature(help, module._stub_help)
    assert ok is False


@pytest.mark.unit
def test_module_without_help_still_passes_check():
    """help is optional: a module without it must not fail the contract check."""
    import bbsengine6.console.tui as tui

    assert not hasattr(types.SimpleNamespace(), "help")
    with patch.object(module.io, "echo"):
        assert module.check(None, "bbsengine6.console.tui") is True
    assert tui is not None
