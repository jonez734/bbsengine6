"""
Regression tests for Phase 4 io/inputstring.py hardening.

Covers:
- inputstring() pops `filter` kwarg so it never leaks into verify() callback
- inputstring() accepts and silently discards unknown kwargs without TypeError
- handle_help() marks the module-global _input_dirty flag
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


def test_filter_kwarg_is_popped_not_forwarded():
    """Passing filter= as a kwarg must NOT raise and must NOT leak it
    through to the verify() callback.

    Phase 4 fix: inputstring() now does `filter_fn = kwargs.pop("filter", None)`
    to discard the unsupported kwarg silently instead of forwarding it to
    the verify callback (which previously crashed with TypeError on an
    unexpected keyword).
    """
    mod = _inputstring_module()
    sig = inspect.signature(mod.inputstring)
    assert "filter" not in sig.parameters, (
        "inputstring should NOT advertise `filter` as a parameter; "
        "unknown kwargs are silently popped"
    )


def test_inputstring_pops_known_kwargs_from_kwargs():
    """inputstring() should pop (not forward) the kwargs it knows it cannot
    use. We verify by reading the function source and confirming the
    pop() calls are present for each popped name.
    """
    mod = _inputstring_module()
    src = inspect.getsource(mod.inputstring)
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

    mod._input_dirty = False
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
        assert mod._input_dirty is True, (
            "handle_help must set module-global _input_dirty, not a function-local"
        )
    finally:
        mod._input_dirty = False


def test_handle_help_returns_early_when_no_help():
    """handle_help should return the buffer unchanged when neither f1_help
    nor help is supplied."""
    mod = _inputstring_module()

    mod._input_dirty = False
    try:
        result = mod.handle_help("buf", 0, 0, 80, f1_help=None, help=None)
        assert result == ("buf", 0, 0)
        assert mod._input_dirty is False
    finally:
        mod._input_dirty = False


def test_handle_help_with_callable_f1_help():
    """If f1_help is a callable, its return value is used as help text
    and _input_dirty is set."""
    mod = _inputstring_module()

    mod._input_dirty = False
    try:
        result = mod.handle_help(
            "buf",
            0,
            0,
            80,
            f1_help=lambda: "called",
        )
        assert result == ("buf", 0, 0)
        assert mod._input_dirty is True
    finally:
        mod._input_dirty = False
