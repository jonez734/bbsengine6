"""inputstring(accept_hint=...) pushes "press enter to accept input" onto the bottom bar stack.

The hint is pushed only when the bar is initialized (bottombar.init() has run) and bottombar is
True. The push is popped when the prompt ends, by accept or abort. A call pops only the frame it
pushed, so an outer caller's pushed state is never removed.

These tests patch the bottombar module and the prompt body, so no terminal is needed.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest

inp = importlib.import_module("bbsengine6.io.inputstring")
from bbsengine6.io.const import INPUTSTRING_ACCEPT_HINT  # noqa: E402


class FakeBar:
    """Records push/pop calls and tracks a stack, like FragmentRegistry does."""

    def __init__(self, initialized=True):
        self.initialized = initialized
        self.stack = []
        self.left = ""
        self.calls = []

    def is_initialized(self):
        return self.initialized

    def push(self, left=None, fragments=None, **kwargs):
        self.calls.append(("push", left))
        self.stack.append(self.left)
        if left is not None:
            self.left = left

    def pop(self, **kwargs):
        self.calls.append(("pop",))
        if not self.stack:
            return False
        self.left = self.stack.pop()
        return True


@pytest.fixture
def bar(monkeypatch):
    fake = FakeBar(initialized=True)
    monkeypatch.setattr(inp, "_show_accept_hint", inp._show_accept_hint)
    import bbsengine6.bottombar as bb
    monkeypatch.setattr(bb, "is_initialized", fake.is_initialized)
    monkeypatch.setattr(bb, "push", fake.push)
    monkeypatch.setattr(bb, "pop", fake.pop)
    return fake


@pytest.fixture
def quiet(monkeypatch):
    """Skip the tty session plumbing and the prompt itself; only the hint wiring is under test."""
    for name in ("begin_raw_session", "end_raw_session", "bracketed_paste_on", "bracketed_paste_off",
                 "mouse_state_push", "mouse_state_pop", "_hide_mode", "_restore_key_snapshot",
                 "_snapshot_stack"):
        monkeypatch.setattr(inp, name, MagicMock(return_value=None) if name != "_snapshot_stack"
                            else MagicMock(return_value=[]))


def _run(body, **kwargs):
    with patch.object(inp, "_inputstring_body", side_effect=body):
        return inp.inputstring("prompt: ", "", **kwargs)


@pytest.mark.unit
def test_hint_is_pushed_when_initialized(bar, quiet):
    _run(lambda *a, **k: "ok")
    assert bar.calls[0] == ("push", INPUTSTRING_ACCEPT_HINT)


@pytest.mark.unit
def test_hint_is_not_pushed_when_bar_not_initialized(bar, quiet):
    bar.initialized = False
    _run(lambda *a, **k: "ok")
    assert ("push", INPUTSTRING_ACCEPT_HINT) not in bar.calls


@pytest.mark.unit
def test_accept_hint_false_pushes_nothing(bar, quiet):
    _run(lambda *a, **k: "ok", accept_hint=False)
    assert bar.calls == []


@pytest.mark.unit
def test_bottombar_false_pushes_nothing(bar, quiet):
    _run(lambda *a, **k: "ok", bottombar=False)
    assert bar.calls == []


@pytest.mark.unit
def test_hint_is_popped_on_accept(bar, quiet):
    _run(lambda *a, **k: "typed")
    assert bar.calls == [("push", INPUTSTRING_ACCEPT_HINT), ("pop",)]


@pytest.mark.unit
def test_hint_is_popped_on_abort(bar, quiet):
    def abort(*a, **k):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run(abort)
    assert bar.calls == [("push", INPUTSTRING_ACCEPT_HINT), ("pop",)]


@pytest.mark.unit
def test_hint_is_popped_on_exception(bar, quiet):
    def boom(*a, **k):
        raise EOFError

    with pytest.raises(EOFError):
        _run(boom)
    assert bar.calls[-1] == ("pop",)


@pytest.mark.unit
def test_never_pops_a_frame_it_did_not_push(bar, quiet):
    """If the hint was never pushed (bar not initialized), the finally must not pop an outer frame."""
    bar.initialized = False
    bar.stack.append("outer-left")  # an outer caller's pushed state
    _run(lambda *a, **k: "ok")
    assert ("pop",) not in bar.calls
    assert bar.stack == ["outer-left"]


@pytest.mark.unit
def test_nested_prompt_restores_the_outer_frame(bar, quiet):
    """An inner prompt pushes on top of an outer frame and pops back to it, not past it."""
    outer_left = "outer prompt"
    bar.left = outer_left

    def inner(*a, **k):
        assert bar.left == INPUTSTRING_ACCEPT_HINT
        return "inner"

    _run(inner)
    assert bar.left == outer_left
    assert bar.stack == []


@pytest.mark.unit
def test_push_failure_does_not_break_input(bar, quiet, monkeypatch):
    import bbsengine6.bottombar as bb

    def fail(**kwargs):
        raise RuntimeError("bar broke")

    monkeypatch.setattr(bb, "push", lambda *a, **k: fail())
    assert _run(lambda *a, **k: "still works") == "still works"
