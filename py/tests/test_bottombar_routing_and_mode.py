"""bottombar routing and the MODE fragment: named registries, per-connection override, and push/pop
against the registry that is active. These paths had no tests before."""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar as bb
import importlib
ins = importlib.import_module("bbsengine6.io.inputstring")


@pytest.fixture(autouse=True)
def _isolate():
    bb._REGISTRY_CACHE.pop("conn-test", None)
    bb._FRAGMENT_STATE.clear()
    token = bb._active_registry.set(None)
    yield
    bb._active_registry.reset(token)
    bb._REGISTRY_CACHE.pop("conn-test", None)
    bb._FRAGMENT_STATE.clear()


@pytest.mark.unit
def test_registry_for_returns_the_same_instance_per_name():
    assert bb.registry_for("conn-test") is bb.registry_for("conn-test")


@pytest.mark.unit
def test_registry_for_default_is_the_default_registry():
    assert bb.registry_for("default") is bb.default_registry()


@pytest.mark.unit
def test_named_registries_are_independent():
    a, b = bb.registry_for("conn-test"), bb.registry_for("default")
    a.register("only-in-a")
    assert "only-in-a" not in b.items


@pytest.mark.unit
def test_set_context_for_stashes_args_and_pool_on_the_named_registry():
    sentinel_args, sentinel_pool = object(), object()
    bb.set_context_for("conn-test", args=sentinel_args, pool=sentinel_pool)
    reg = bb.registry_for("conn-test")
    assert reg.args is sentinel_args and reg.pool is sentinel_pool


@pytest.mark.unit
def test_render_for_renders_only_the_named_registry():
    bb.registry_for("conn-test").register("named")
    with patch.object(bb, "_get_notification_status", return_value=""):
        assert bb.render_for("conn-test") == "named"
        assert "named" not in bb.render_for("default")


@pytest.mark.unit
def test_active_registry_overrides_registration_and_resets():
    named = bb.registry_for("conn-test")
    token = bb.set_active_registry(named)
    try:
        bb.register_bottombar_fragment("routed")
        assert "routed" in named.items
    finally:
        bb.reset_active_registry(token)
    # Reset changes where NEW items go; it does not unregister items already placed.
    assert "routed" in named.items
    assert "routed" not in bb.default_registry().items


@pytest.mark.unit
def test_reset_restores_default_routing():
    named = bb.registry_for("conn-test")
    token = bb.set_active_registry(named)
    bb.reset_active_registry(token)
    assert bb._resolve_registry() is bb.default_registry()


@pytest.mark.unit
def test_push_and_pop_act_on_the_active_registry_not_the_default():
    named = bb.registry_for("conn-test")
    named.register("base")
    token = bb.set_active_registry(named)
    try:
        with patch.object(bb, "_render_bottombar") as render:
            bb.push(left="Lobby", fragments=["F1: help"])
        assert "F1: help" in named.items
        assert "F1: help" not in bb.default_registry().items
        assert render.called
    finally:
        bb.reset_active_registry(token)


@pytest.mark.unit
def test_mode_fragment_shows_insert_and_overwrite_indicators():
    state = {"insert": True, "item": None}
    with patch.object(ins, "_mode_state", return_value=state):
        assert ins._mode_fragment() == ins.INPUTSTRING_INSERT_MODE_INDICATOR
        state["insert"] = False
        assert ins._mode_fragment() == ins.INPUTSTRING_OVERWRITE_MODE_INDICATOR


@pytest.mark.unit
def test_show_mode_registers_the_fragment_once_and_repaints():
    state = {"insert": True, "item": None}
    reg = bb.default_registry()
    with patch.object(ins, "_mode_state", return_value=state), \
         patch.object(bb, "setbottombar") as repaint:
        ins._show_mode(True, paint=True)
        ins._show_mode(False, paint=True)
    assert state["item"] is not None
    assert state["insert"] is False
    assert repaint.call_count == 2
    assert reg.items.count(ins._mode_fragment) <= 1


@pytest.mark.unit
def test_hide_mode_unregisters_and_clears_the_state():
    state = {"insert": True, "item": ins._mode_fragment}
    reg = bb.default_registry()
    reg.register(ins._mode_fragment)
    with patch.object(ins, "_mode_state", return_value=state), \
         patch.object(bb, "setbottombar", create=True):
        ins._hide_mode(paint=True)
    assert state["item"] is None
    assert ins._mode_fragment not in reg.items
