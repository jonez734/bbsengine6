"""
Regression tests for Phase 2 module.runcallback() hardening.

The function used to evaluate callbacks as Python expressions via eval(),
which is unsafe if a caller-supplied string ever made it through to this
function. The fix replaced `eval()` with explicit `importlib` + `getattr`
(or, for the bare-name branch, an inspect-stack globals lookup).

These tests pin down the new contract:

- Callable callbacks are invoked directly (no string parsing).
- A bare-name branch (callback="" → fname="main") looks up "main" in
  the caller's frame globals — never eval()s arbitrary expressions.
- Non-existent / non-callable names return None rather than raising.
- runcallback's source contains no eval() calls (comments excluded).
"""

import argparse
import importlib
import inspect
import re

import pytest

from bbsengine6 import module


pytestmark = pytest.mark.unit


def _args():
    return argparse.Namespace(debug=False)


def test_runcallback_with_callable_invokes_directly():
    """Passing a Python callable works without any string parsing."""
    args = _args()
    sentinel = []

    def my_cb(a, **kwargs):
        sentinel.append((a, kwargs))
        return "ok"

    result = module.runcallback(args, my_cb, foo="bar")
    assert result == "ok"
    assert sentinel == [(args, {"foo": "bar"})]


def test_runcallback_with_none_returns_none():
    args = _args()
    assert module.runcallback(args, None) is None


def test_runcallback_with_non_string_non_callable_returns_none():
    """A non-string, non-callable callback must return None, not raise."""
    args = _args()
    assert module.runcallback(args, 12345) is None  # type: ignore[arg-type]


def test_runcallback_with_known_module_missing_attr_returns_none():
    """A known module but unknown attribute returns None (logged as
    error) — that's the Phase 2 hardening in action. Previously this
    path would propagate AttributeError up to the caller; now it is
    caught and logged, so a typo in a registered callback doesn't crash
    the host loop."""
    args = _args()
    result = module.runcallback(args, "json.totally_nonexistent_func_xyz")
    assert result is None


def test_runcallback_bare_name_branch_calls_caller_main():
    """callback="" triggers the bare-name branch which looks up "main"
    in the caller's frame globals. We define "main" in this frame's
    globals, then verify runcallback invokes it."""
    args = _args()
    sentinel = []

    def _fake_main(a, **kwargs):
        sentinel.append(("main-called", kwargs))
        return "main-result"

    globals()["main"] = _fake_main
    try:
        result = module.runcallback(args, "", tag="x")
        assert result == "main-result"
        assert sentinel == [("main-called", {"tag": "x"})]
    finally:
        del globals()["main"]


def test_runcallback_bare_name_branch_unknown_returns_none():
    """callback="" with no "main" in caller's globals returns None,
    not NameError."""
    args = _args()
    assert "main" not in globals(), "test pre-condition: 'main' must not exist"
    result = module.runcallback(args, "")
    assert result is None


def test_runcallback_bare_name_branch_non_callable_returns_none():
    """callback="" with a non-callable "main" in caller globals returns None."""
    args = _args()
    globals()["main"] = 42
    try:
        assert module.runcallback(args, "") is None
    finally:
        del globals()["main"]


def test_runcallback_source_does_not_call_eval():
    """The whole point of the Phase 2 hardening: runcallback must not
    *invoke* eval() with caller-controlled strings. Comments / docstrings
    mentioning the word are fine."""
    src = inspect.getsource(module.runcallback)
    # Strip comments (# ...) and triple-quoted strings (docstrings) so
    # mentions like "rather than eval()-ing arbitrary expressions" don't
    # cause false positives. Then assert no remaining `eval(` invocation.
    no_comments = re.sub(r"#.*", "", src)
    no_strings = re.sub(r'"""[\s\S]*?"""', "", no_comments)
    no_strings = re.sub(r"'''[\s\S]*?'''", "", no_strings)
    assert "eval(" not in no_strings, (
        "runcallback must not call eval() — use importlib + getattr or "
        "inspect.stack() globals lookup"
    )


def test_runcallback_uses_getattr_for_dotted_resolution():
    """Pin down the dotted-name resolution uses getattr, not eval:"""
    src = inspect.getsource(module.runcallback)
    # Strip comments and docstrings.
    no_comments = re.sub(r"#.*", "", src)
    no_strings = re.sub(r'"""[\s\S]*?"""', "", no_comments)
    no_strings = re.sub(r"'''[\s\S]*?'''", "", no_strings)
    assert "getattr(" in no_strings, (
        "runcallback must use getattr() to resolve dotted callbacks, "
        "not eval() or direct subscript"
    )


def test_runcallback_uses_inspect_stack_for_bare_name():
    """Pin down the bare-name branch uses inspect.stack().frame.f_globals
    and never exec/eval."""
    src = inspect.getsource(module.runcallback)
    no_comments = re.sub(r"#.*", "", src)
    no_strings = re.sub(r'"""[\s\S]*?"""', "", no_comments)
    no_strings = re.sub(r"'''[\s\S]*?'''", "", no_strings)
    assert "inspect.stack" in no_strings, (
        "runcallback must use inspect.stack() to find the caller's frame "
        "for bare-name lookup"
    )
    assert "exec(" not in no_strings, (
        "runcallback must not use exec() to evaluate bare-name callbacks"
    )
