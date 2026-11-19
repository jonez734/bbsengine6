"""inputstring() no longer pushes "press enter to accept value" onto the bottom bar.

The hint was pushed at every call when the bar was initialized, and popped when the prompt ended. It is disabled
(the push is commented out in inputstring), so no call touches the bottom bar's left side, whatever the arguments.
These tests patch the bottombar module and the prompt body, so no terminal is needed.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest

inp = importlib.import_module("bbsengine6.io.inputstring")


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
    import bbsengine6.bottombar as bb
    monkeypatch.setattr(bb, "is_initialized", fake.is_initialized)
    monkeypatch.setattr(bb, "push", fake.push)
    monkeypatch.setattr(bb, "pop", fake.pop)
    return fake


@pytest.fixture
def quiet(monkeypatch):
    """Skip the tty session plumbing and the prompt itself; only the bottom bar wiring is under test."""
    for name in ("begin_raw_session", "end_raw_session", "bracketed_paste_on", "bracketed_paste_off",
                 "mouse_state_push", "mouse_state_pop", "_hide_mode", "_restore_key_snapshot",
                 "_snapshot_stack"):
        monkeypatch.setattr(inp, name, MagicMock(return_value=None) if name != "_snapshot_stack"
                            else MagicMock(return_value=[]))


def _run(body, **kwargs):
    with patch.object(inp, "_inputstring_body", side_effect=body):
        return inp.inputstring("prompt: ", "", **kwargs)


@pytest.mark.unit
@pytest.mark.parametrize("kwargs", [{}, {"accept_hint": True}, {"accept_hint": False}, {"bottombar": False}])
def test_no_hint_is_pushed_for_any_arguments(bar, quiet, kwargs):
    _run(lambda *a, **k: "ok", **kwargs)
    assert bar.calls == []


@pytest.mark.unit
def test_nothing_is_pushed_or_popped_when_the_prompt_is_accepted(bar, quiet):
    assert _run(lambda *a, **k: "typed") == "typed"
    assert bar.calls == []


@pytest.mark.unit
def test_nothing_is_pushed_or_popped_when_the_prompt_is_aborted(bar, quiet):
    def abort(*a, **k):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        _run(abort)
    assert bar.calls == []


@pytest.mark.unit
def test_an_outer_bottom_bar_frame_is_left_alone(bar, quiet):
    """A prompt inside an outer caller's pushed state does not pop that state."""
    bar.left = "outer prompt"
    bar.stack.append("outer-left")
    _run(lambda *a, **k: "ok")
    assert ("pop",) not in bar.calls
    assert bar.stack == ["outer-left"]
    assert bar.left == "outer prompt"


if __name__ == "__main__":
    pytest.main([__file__])
