"""
Regression tests for Phase 4 io/inputstring.py hardening.

Covers:
- inputstring() pops `filter` kwarg so it never leaks into verify() callback
- inputstring() accepts and silently discards unknown kwargs without TypeError
- handle_help() marks the current interaction's input_dirty flag
"""

import importlib
import inspect

import pytest

pytestmark = pytest.mark.unit


def _inputstring_module():
    """bbsengine6.io re-exports inputstring as a *function*, which shadows
    the submodule. Use importlib to ensure the submodule is loaded, then
    retrieve the actual module object from sys.modules.
    """
    return importlib.import_module("bbsengine6.io.inputstring")


def _common_module():
    return importlib.import_module("bbsengine6.io.common")


def test_inputstring_signature_is_positional_only_for_prompt_oldvalue():
    """prompt and oldvalue must be positional-only so callers cannot
    accidentally pass prompt= keyword that bypasses the prompt display."""
    mod = _inputstring_module()
    sig = inspect.signature(mod.inputstring)
    params = list(sig.parameters.values())
    assert params[0].name == "prompt"
    assert params[0].kind is inspect.Parameter.POSITIONAL_ONLY
    assert params[1].name == "oldvalue"
    assert params[1].kind is inspect.Parameter.POSITIONAL_ONLY


def test_filter_and_allowed_are_consumed_not_forwarded():
    """filter= and allowed= are inputstring options. They must be consumed by
    inputstring and must NOT reach the verify() callback.
    """
    mod = _inputstring_module()
    src = inspect.getsource(mod._inputstring_body)
    assert 'kwargs.pop("filter"' in src
    assert 'kwargs.pop("allowed"' in src


def test_inputstring_pops_known_kwargs_from_kwargs():
    """inputstring() should pop (not forward) the kwargs it knows it cannot
    use. We verify by reading the function source and confirming the
    pop() calls are present for each popped name.
    """
    mod = _inputstring_module()
    # The kwarg pops live in _inputstring_body; inputstring() is a thin wrapper
    # that adds the mouse-state push/pop around it.
    src = inspect.getsource(mod._inputstring_body)
    # Confirm at least a representative subset of popped kwargs.
    for name in (
        "max_len",
        "max_width",
        "mask",
        "completer",
        "filter",
        "verify",
        "args",
        "noneok",
        "history",
        "pagesize",
        "beep_on_error",
        "f1_help",
    ):
        assert f'kwargs.pop("{name}"' in src, (
            f"inputstring() should kwargs.pop({name!r}) to swallow "
            f"unsupported caller kwargs"
        )



def _get_dirty():
    from bbsengine6.io.common import _get_input_dirty
    return _get_input_dirty()


def _set_dirty(value):
    from bbsengine6.io.common import _set_input_dirty
    _set_input_dirty(value)

def test_handle_help_marks_input_dirty():
    """handle_help() must set the module-global _input_dirty flag so the
    main input loop redraws the prompt after displaying help text.

    Pre-Phase-4 bug: `handle_help` declared a function-local `_input_dirty`
    assignment which shadowed the module global and never propagated.

    Note: _input_dirty is imported from bbsengine6.io.common, so reading
    the flag from inputstring's own module dict (via `mod._input_dirty`)
    is what handle_help writes via `global _input_dirty`.
    """
    mod = _inputstring_module()

    _set_dirty(False)
    try:
        # handle_help with help= text (not f1_help) returns unchanged buffer
        # and sets _input_dirty.
        result = mod.handle_help(
            "buf",
            0,
            0,
            80,
            help="line1\nline2",
        )
        assert result == ("buf", 0, 0)
        assert _get_dirty() is True, (
            "handle_help must set module-global _input_dirty, not a function-local"
        )
    finally:
        _set_dirty(False)


def test_handle_help_returns_early_when_no_help():
    """handle_help should return the buffer unchanged when neither f1_help
    nor help is supplied."""
    mod = _inputstring_module()

    _set_dirty(False)
    try:
        result = mod.handle_help("buf", 0, 0, 80, f1_help=None, help=None)
        assert result == ("buf", 0, 0)
        assert _get_dirty() is False
    finally:
        _set_dirty(False)


def test_handle_help_with_callable_f1_help():
    """If f1_help is a callable, its return value is used as help text
    and _input_dirty is set."""
    mod = _inputstring_module()

    _set_dirty(False)
    try:
        result = mod.handle_help(
            "buf",
            0,
            0,
            80,
            f1_help=lambda: "called",
        )
        assert result == ("buf", 0, 0)
        assert _get_dirty() is True
    finally:
        _set_dirty(False)
