"""The bottombar registry's push/pop stack: what a frame holds, how it is copied, and how it nests.

test_bottombar.py covers the basic push/pop contract. This file pins the details that make the stack
safe to share between callers:

- a frame keeps the original left value, so a callable is re-evaluated after pop();
- a frame holds a copy of the fragment list, so later edits to the live list do not change it;
- nested pushes unwind in order, across named registries, and per connection;
- the accept hint (inputstring) pushes only when the bar is initialized, and the MODE fragment
  registered after a push is not part of the saved frame.

Repaints are patched out (_render_bottombar), so no terminal is needed.
"""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar as bb
from bbsengine6.bottombar import FragmentRegistry


@pytest.fixture(autouse=True)
def _isolate():
    bb._REGISTRY_CACHE.pop("stack-test", None)
    bb._FRAGMENT_STATE.clear()
    token = bb._active_registry.set(None)
    yield
    bb._active_registry.reset(token)
    bb._REGISTRY_CACHE.pop("stack-test", None)
    bb._FRAGMENT_STATE.clear()


@pytest.fixture
def render():
    with patch("bbsengine6.bottombar._render_bottombar") as mock:
        yield mock


def _reg(name="stack"):
    return FragmentRegistry(name=name)


# --- what a frame holds -------------------------------------------------------------------------


@pytest.mark.unit
def test_string_left_is_stored_verbatim_in_the_frame(render):
    reg = _reg()
    reg.left = "base"
    reg.push(left="new")
    saved_left, _items = reg._stack[-1]
    assert saved_left == "base"


@pytest.mark.unit
def test_callable_left_is_stored_as_the_callable_not_its_output(render):
    calls = []

    def left(**kwargs):
        calls.append(kwargs)
        return "rendered"

    reg = _reg()
    reg.left = left
    reg.push(left="other")
    saved_left, _items = reg._stack[-1]
    assert saved_left is left
    assert calls == [], "push must not call the callable"


@pytest.mark.unit
def test_pop_calls_a_saved_callable_again_and_passes_kwargs(render):
    seen = []

    def left(**kwargs):
        seen.append(kwargs)
        return "rendered"

    reg = _reg()
    reg.left = left
    reg.push(left="other")
    reg.pop(extra=7)
    # The repaint after pop() renders the restored callable with the caller's kwargs.
    assert render.call_args.kwargs["left"] is left
    assert render.call_args.kwargs["extra"] == 7


@pytest.mark.unit
def test_empty_string_left_is_kept_not_treated_as_none(render):
    """push(left="") installs an empty left; push() with no left keeps the current one."""
    reg = _reg()
    reg.left = "base"
    reg.push(left="")
    assert reg.left == ""
    reg.push()
    assert reg.left == "", "left=None must keep the current left, including an empty one"


@pytest.mark.unit
def test_fragments_are_copied_into_the_frame_not_aliased(render):
    reg = _reg()
    reg.register("a")
    reg.register("b")
    reg.push()
    _left, saved_items = reg._stack[-1]
    assert saved_items == ["a", "b"]
    assert saved_items is not reg.items, "the frame must hold its own copy of the list"


@pytest.mark.unit
def test_mutating_live_fragments_after_push_does_not_change_the_frame(render):
    reg = _reg()
    reg.register("a")
    reg.push()
    reg.register("b")
    reg.unregister("a")
    reg.pop()
    assert list(reg.items) == ["a"], "pop must restore the fragments as they were at push time"


@pytest.mark.unit
def test_pop_restores_the_fragment_list_object_contents_in_place(render):
    """pop writes into the live list, so anything holding that list sees the restored items."""
    reg = _reg()
    reg.register("a")
    live = reg.items
    reg.push(fragments=["x", "y"])
    reg.pop()
    assert reg.items is live
    assert list(live) == ["a"]


# --- nesting and ordering -----------------------------------------------------------------------


@pytest.mark.unit
def test_nested_pushes_unwind_in_last_in_first_out_order(render):
    reg = _reg()
    reg.left = "base"
    reg.push(left="one")
    reg.push(left="two")
    reg.push(left="three")
    assert reg.pop() is True
    assert reg.left == "two"
    assert reg.pop() is True
    assert reg.left == "one"
    assert reg.pop() is True
    assert reg.left == "base"
    assert reg.pop() is False


@pytest.mark.unit
def test_each_pop_repaints_with_the_frame_it_restores(render):
    reg = _reg()
    reg.left = "base"
    reg.push(left="one")
    reg.push(left="two")
    render.reset_mock()
    reg.pop()
    assert render.call_args.kwargs["left"] == "one"


@pytest.mark.unit
def test_failed_pop_on_empty_stack_neither_changes_state_nor_repaints(render):
    reg = _reg()
    reg.left = "base"
    reg.register("a")
    assert reg.pop() is False
    assert reg.left == "base"
    assert list(reg.items) == ["a"]
    render.assert_not_called()


@pytest.mark.unit
def test_registries_under_the_same_name_share_one_stack(render):
    """registry_for returns one instance per name, so the stack is shared by every caller of that name."""
    first = bb.registry_for("stack-test")
    second = bb.registry_for("stack-test")
    first.left = "base"
    first.push(left="pushed")
    assert second.left == "pushed"
    assert second.pop() is True
    assert first.left == "base"


@pytest.mark.unit
def test_module_push_routes_to_the_active_registry_not_the_default(render):
    default = bb.default_registry()
    default.left = "default-base"
    other = _reg("other")
    other.left = "other-base"
    token = bb.set_active_registry(other)
    try:
        bb.push(left="pushed")
        assert other.left == "pushed"
        assert default.left == "default-base"
        assert bb.pop() is True
        assert other.left == "other-base"
    finally:
        bb.reset_active_registry(token)


# --- the accept hint on the stack ---------------------------------------------------------------


@pytest.mark.unit
def test_accept_hint_is_pushed_only_when_bar_is_initialized(render, monkeypatch):
    import importlib
    from bbsengine6.io.const import INPUTSTRING_ACCEPT_HINT

    ins = importlib.import_module("bbsengine6.io.inputstring")

    monkeypatch.setattr(bb, "_initialized", False)
    assert ins._show_accept_hint(paint=True) is False
    assert bb.default_registry()._stack == []

    monkeypatch.setattr(bb, "_initialized", True)
    try:
        assert ins._show_accept_hint(paint=True) is True
        assert bb.default_registry().left == INPUTSTRING_ACCEPT_HINT
        ins._hide_accept_hint(True)
        assert bb.default_registry().left != INPUTSTRING_ACCEPT_HINT
    finally:
        bb.default_registry()._stack.clear()


@pytest.mark.unit
def test_mode_fragment_registered_after_push_is_not_in_the_saved_frame(render):
    """The MODE fragment is registered after the hint is pushed, so pop() must not restore it."""
    reg = bb.default_registry()
    reg.items.clear()
    reg.left = "base"
    reg.push(left="press enter")

    def mode(**_kwargs):
        return "[INS]"

    reg.register(mode)
    assert mode in reg.items
    reg.pop()
    assert mode not in reg.items, "pop restores the frame saved before the MODE fragment, so it must be gone"
    assert reg.left == "base"
    reg.items.clear()
    reg._stack.clear()
