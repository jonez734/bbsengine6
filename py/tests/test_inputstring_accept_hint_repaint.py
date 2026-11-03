"""The accept hint stays on the bottom bar's left side while the MODE fragment repaints.

_show_mode and _hide_mode used to call setbottombar(None, ""), which set the registry's left to ""
and erased the hint that inputstring() had pushed. They now call repaint(), which redraws from the
current left. These tests pin that, and that repaint() leaves player and pool alone.
"""

import importlib
from unittest.mock import patch

import pytest

bb = importlib.import_module("bbsengine6.bottombar")
ins = importlib.import_module("bbsengine6.io.inputstring")
from bbsengine6.io.const import INPUTSTRING_ACCEPT_HINT  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    bb._FRAGMENT_STATE.clear()
    token = bb._active_registry.set(None)
    reg = bb.default_registry()
    saved = (reg.left, list(reg.items), list(reg._stack), reg.player, reg.pool, reg.args)
    reg.items.clear()
    reg._stack.clear()
    reg.left = None
    monkeypatch.setattr(bb, "_initialized", True)
    monkeypatch.setattr(ins, "_mode_state", ins._mode_state)
    yield reg
    reg.left, items, stack, reg.player, reg.pool, reg.args = saved
    reg.items[:] = items
    reg._stack[:] = stack
    ins._mode_state()["item"] = None
    bb._active_registry.reset(token)


@pytest.fixture
def render():
    with patch("bbsengine6.bottombar._render_bottombar", return_value=True) as mock:
        yield mock


@pytest.mark.unit
def test_mode_repaint_keeps_the_pushed_hint_as_left(_isolate, render):
    reg = _isolate
    assert ins._show_accept_hint(paint=True) is True
    assert reg.left == INPUTSTRING_ACCEPT_HINT

    ins._show_mode(True, paint=True)

    assert reg.left == INPUTSTRING_ACCEPT_HINT, "MODE repaint must not erase the accept hint"
    assert render.call_args.kwargs["left"] == INPUTSTRING_ACCEPT_HINT


@pytest.mark.unit
def test_hide_mode_repaint_keeps_the_pushed_hint_as_left(_isolate, render):
    reg = _isolate
    ins._show_accept_hint(paint=True)
    ins._show_mode(True, paint=True)
    ins._hide_mode(paint=True)
    assert reg.left == INPUTSTRING_ACCEPT_HINT
    assert render.call_args.kwargs["left"] == INPUTSTRING_ACCEPT_HINT


@pytest.mark.unit
def test_pop_after_mode_repaint_restores_the_previous_left(_isolate, render):
    reg = _isolate
    reg.left = "outer prompt"
    ins._show_accept_hint(paint=True)
    ins._show_mode(True, paint=True)
    ins._hide_accept_hint(True)
    assert reg.left == "outer prompt"


@pytest.mark.unit
def test_repaint_does_not_change_player_or_pool(_isolate, render):
    reg = _isolate
    reg.set_context(args=None, player="p1", pool="pool1")
    reg.left = "keep"
    bb.repaint()
    assert reg.left == "keep"
    assert reg.player == "p1"
    assert reg.pool == "pool1"


@pytest.mark.unit
def test_repaint_paints_the_current_left_and_fragments(_isolate, render):
    reg = _isolate
    reg.left = "shown"
    reg.register("frag")
    bb.repaint()
    assert render.call_args.kwargs["left"] == "shown"
    assert render.call_args.args[0] is reg


@pytest.mark.unit
def test_repaint_draws_a_never_set_left_as_empty_not_none(_isolate, render):
    """A registry with no left yet must not paint the text "None" on the bar."""
    reg = _isolate
    reg.left = None
    bb.repaint()
    assert render.call_args.kwargs["left"] == ""


def test_setbottombar_is_unchanged_and_keeps_stashed_player_when_not_given(_isolate, render):
    """setbottombar() still sets left and only updates context it is given (set_context's contract)."""
    reg = _isolate
    reg.set_context(args=None, player="p1", pool="pool1")
    bb.setbottombar(None, "")
    assert reg.left == ""
    assert reg.player == "p1"
    assert reg.pool == "pool1"
