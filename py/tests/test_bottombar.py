"""
Comprehensive tests for the bbsengine6.bottombar module.

Covers:
- FragmentRegistry: register / unregister / clear / render / set_context
- Default-registry behavior (process-global singleton)
- Per-package FragmentRegistry (independent state, no leakage)
- setbottombar shim stashes args/player/pool into the registry
- Notification status is prepended to the right side
- Thread safety for register / unregister / render
- Back-compat: the bbsengine6.io.screen shim still routes through
  bbsengine6.bottombar.
"""

import sys
import threading
from unittest.mock import patch

import pytest

sys.path.insert(0, "py/src")

from bbsengine6 import bottombar
from bbsengine6.bottombar import (
    FragmentRegistry,
    _LockedList,
    default_registry,
    register_bottombar_fragment,
    unregister_bottombar_fragment,
    clear_bottombar_fragments,
    setbottombar,
)


@pytest.fixture(autouse=True)
def _clean_default_registry():
    """Save and restore the default registry's state around each test."""
    reg = default_registry()
    saved_items = list(reg.items)
    saved_args = reg.args
    saved_player = reg.player
    saved_pool = reg.pool
    reg.clear()
    reg.args = None
    reg.player = None
    reg.pool = None
    yield
    reg.clear()
    for item in saved_items:
        reg.register(item)
    reg.args = saved_args
    reg.player = saved_player
    reg.pool = saved_pool


# ---------------------------------------------------------------------------
# FragmentRegistry
# ---------------------------------------------------------------------------


class TestFragmentRegistryBasics:
    def test_empty_render_returns_empty_string(self):
        r = FragmentRegistry(name="test")
        assert r.render() == ""
        assert len(r) == 0
        assert list(r) == []
        assert "x" not in r

    def test_register_returns_item(self):
        r = FragmentRegistry(name="test")
        assert r.register("hi") == "hi"
        assert "hi" in r

    def test_register_prevents_duplicates(self):
        r = FragmentRegistry(name="test")
        r.register("dup")
        r.register("dup")
        assert r.items.count("dup") == 1

    def test_register_callable(self):
        r = FragmentRegistry(name="test")
        r.register(lambda **kw: "result")
        assert "result" in r.render()

    def test_register_unregister_roundtrip(self):
        r = FragmentRegistry(name="test")
        r.register("a")
        r.register("b")
        assert r.unregister("a") is True
        assert r.unregister("a") is False
        assert "a" not in r
        assert "b" in r

    def test_clear(self):
        r = FragmentRegistry(name="test")
        r.register("a")
        r.register("b")
        r.clear()
        assert len(r) == 0
        assert r.render() == ""

    def test_iteration_order(self):
        r = FragmentRegistry(name="test")
        for x in ("a", "b", "c"):
            r.register(x)
        assert list(r) == ["a", "b", "c"]

    def test_render_skips_empty_strings(self):
        r = FragmentRegistry(name="test")
        r.register("a")
        r.register("")
        r.register("b")
        assert r.render() == "a | b"

    def test_render_skips_falsy_callable_return(self):
        r = FragmentRegistry(name="test")
        r.register(lambda **kw: "")
        r.register(lambda **kw: None)
        r.register(lambda **kw: "visible")
        assert r.render() == "visible"

    def test_render_swallows_callable_exceptions(self):
        r = FragmentRegistry(name="test")
        r.register("ok")
        r.register(lambda **kw: 1 / 0)
        r.register("still-ok")
        with patch("bbsengine6.bottombar.echo_traceback"):
            assert r.render() == "ok | still-ok"


# ---------------------------------------------------------------------------
# set_context and kwargs forwarding
# ---------------------------------------------------------------------------


class TestFragmentRegistryContext:
    def test_set_context_stores_args_player_pool(self):
        r = FragmentRegistry(name="test")
        sentinel_args = object()
        sentinel_player = object()
        sentinel_pool = object()
        r.set_context(args=sentinel_args, player=sentinel_player, pool=sentinel_pool)
        assert r.args is sentinel_args
        assert r.player is sentinel_player
        assert r.pool is sentinel_pool

    def test_render_passes_registry_context_as_kwargs(self):
        r = FragmentRegistry(name="test")
        sentinel_args = object()
        sentinel_player = object()
        captured = {}

        def frag(**kw):
            captured.update(kw)
            return "ok"

        r.set_context(args=sentinel_args, player=sentinel_player, pool="ignored")
        r.register(frag)
        r.render()
        assert captured.get("args") is sentinel_args
        assert captured.get("player") is sentinel_player

    def test_render_kwargs_override_registry_context(self):
        r = FragmentRegistry(name="test")
        captured = {}

        def frag(**kw):
            captured.update(kw)
            return "ok"

        r.set_context(args="from-registry", player="from-registry-player")
        r.register(frag)
        r.render(args="from-call")
        assert captured["args"] == "from-call"
        # player should fall through to registry context
        assert captured["player"] == "from-registry-player"

    def test_set_context_does_not_overwrite_player_with_none(self):
        r = FragmentRegistry(name="test")
        sentinel = object()
        r.set_context(player=sentinel)
        r.set_context(player=None)  # explicitly None
        assert r.player is sentinel


# ---------------------------------------------------------------------------
# Notification status
# ---------------------------------------------------------------------------


class TestNotificationStatus:
    def test_notification_prepended_when_present(self):
        r = FragmentRegistry(name="test")
        r.register("a")
        r.register("b")
        with patch("bbsengine6.bottombar._get_notification_status") as mock:
            mock.return_value = "F2: notify (5)"
            assert r.render() == "F2: notify (5) | a | b"

    def test_no_notification_when_empty(self):
        r = FragmentRegistry(name="test")
        r.register("a")
        with patch("bbsengine6.bottombar._get_notification_status") as mock:
            mock.return_value = ""
            assert r.render() == "a"

    def test_notification_with_no_fragments(self):
        r = FragmentRegistry(name="test")
        with patch("bbsengine6.bottombar._get_notification_status") as mock:
            mock.return_value = "F2: notify (3)"
            assert r.render() == "F2: notify (3)"


# ---------------------------------------------------------------------------
# Default registry (singleton)
# ---------------------------------------------------------------------------


class TestDefaultRegistry:
    def test_default_registry_is_singleton(self):
        a = default_registry()
        b = default_registry()
        assert a is b

    def test_module_level_helpers_use_default(self):
        register_bottombar_fragment("x")
        assert "x" in default_registry()
        assert unregister_bottombar_fragment("x") is True
        assert "x" not in default_registry()

    def test_clear_bottombar_fragments_clears_default(self):
        register_bottombar_fragment("a")
        register_bottombar_fragment("b")
        clear_bottombar_fragments()
        assert len(default_registry()) == 0


# ---------------------------------------------------------------------------
# Per-package independence
# ---------------------------------------------------------------------------


class TestPerPackageRegistries:
    def test_two_registries_are_independent(self):
        a = FragmentRegistry(name="a")
        b = FragmentRegistry(name="b")
        a.register("a-item")
        b.register("b-item")
        assert "a-item" in a
        assert "a-item" not in b
        assert "b-item" in b
        assert "b-item" not in a

    def test_clearing_one_does_not_affect_other(self):
        a = FragmentRegistry(name="a")
        b = FragmentRegistry(name="b")
        a.register("a-item")
        b.register("b-item")
        a.clear()
        assert len(a) == 0
        assert len(b) == 1

    def test_context_does_not_leak(self):
        a = FragmentRegistry(name="a")
        b = FragmentRegistry(name="b")
        sentinel = object()
        a.set_context(player=sentinel)
        assert b.player is None

    def test_each_registry_has_own_lock(self):
        a = FragmentRegistry(name="a")
        b = FragmentRegistry(name="b")
        assert a.lock is not b.lock


# ---------------------------------------------------------------------------
# setbottombar shim
# ---------------------------------------------------------------------------


class TestSetbottombarShim:
    def test_setbottombar_stashes_args(self):
        sentinel_args = object()
        with patch("bbsengine6.bottombar._render_bottombar") as mock:
            mock.return_value = True
            setbottombar(sentinel_args, "left text")
            assert default_registry().args is sentinel_args

    def test_setbottombar_stashes_player(self):
        sentinel_player = object()
        with patch("bbsengine6.bottombar._render_bottombar") as mock:
            mock.return_value = True
            setbottombar(None, "left text", player=sentinel_player)
            assert default_registry().player is sentinel_player

    def test_setbottombar_stashes_pool(self):
        sentinel_pool = object()
        with patch("bbsengine6.bottombar._render_bottombar") as mock:
            mock.return_value = True
            setbottombar(None, "left text", pool=sentinel_pool)
            assert default_registry().pool is sentinel_pool

    def test_setbottombar_returns_true(self):
        with patch("bbsengine6.bottombar._render_bottombar") as mock:
            mock.return_value = True
            assert setbottombar(None, "anything") is True

    def test_setbottombar_does_not_overwrite_player_with_none(self):
        sentinel_player = object()
        with patch("bbsengine6.bottombar._render_bottombar") as mock:
            mock.return_value = True
            setbottombar(None, "first", player=sentinel_player)
            setbottombar(None, "second", player=None)
            assert default_registry().player is sentinel_player


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------


class TestThreadSafety:
    def test_register_from_many_threads(self):
        r = FragmentRegistry(name="threaded")
        N = 100

        def worker(start):
            for i in range(N):
                r.register(f"item-{start}-{i}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(r) == 4 * N

    def test_render_under_concurrent_register(self):
        r = FragmentRegistry(name="render-threaded")

        def registerer():
            for i in range(200):
                r.register(f"item-{i}")

        def renderer(results):
            for _ in range(200):
                # Just verify render() doesn't crash; we don't assert on content
                # because of races.
                results.append(r.render())

        results = []
        t1 = threading.Thread(target=registerer)
        t2 = threading.Thread(target=renderer, args=(results,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 200

    def test_locked_list_snapshot_is_independent(self):
        ll = _LockedList(["a", "b", "c"])
        snap = ll.snapshot()
        snap.append("d")
        assert "d" not in ll
        assert "d" in snap
        assert len(ll) == 3


# ---------------------------------------------------------------------------
# Back-compat: bbsengine6.io.screen shim routes through bottombar
# ---------------------------------------------------------------------------


class TestScreenShimRoutesThroughBottombar:
    def test_screen_register_calls_bottombar(self):
        from bbsengine6.io import screen

        with patch("bbsengine6.bottombar.register_bottombar_fragment") as mock:
            screen.register_bottombar_fragment("via-screen")
            mock.assert_called_once_with("via-screen")

    def test_screen_unregister_calls_bottombar(self):
        from bbsengine6.io import screen

        with patch("bbsengine6.bottombar.unregister_bottombar_fragment") as mock:
            screen.unregister_bottombar_fragment("via-screen")
            mock.assert_called_once_with("via-screen")

    def test_screen_clear_calls_bottombar(self):
        from bbsengine6.io import screen

        with patch("bbsengine6.bottombar.clear_bottombar_fragments") as mock:
            screen.clear_bottombar_fragments()
            mock.assert_called_once_with()

    def test_screen_setbottombar_uses_updatebottombar(self):
        """Pre-existing test_screen.py patches bbsengine6.io.screen.updatebottombar
        and expects setbottombar to flow through it. Verify the shim honors
        that contract."""
        from bbsengine6.io import screen

        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            screen.setbottombar("left")
            mock_update.assert_called_once()
            assert "left" in mock_update.call_args[0][0]

    def test_screen_setbottombar_renders_fragments(self):
        from bbsengine6.io import screen

        screen.register_bottombar_fragment("right-fragment")
        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            screen.setbottombar("left")
            assert "right-fragment" in mock_update.call_args[0][0]

    def test_screen_setbottombar_with_explicit_right(self):
        from bbsengine6.io import screen

        screen.register_bottombar_fragment("from-stack")
        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            screen.setbottombar("left", "explicit-right")
            rendered = mock_update.call_args[0][0]
            assert "explicit-right" in rendered
            assert "from-stack" not in rendered

    def test_screen_render_bottombar_fragments_via_registry(self):
        from bbsengine6.io import screen

        screen.register_bottombar_fragment("item1")
        with patch("bbsengine6.io.screen.get_notification_status") as mock_notif:
            mock_notif.return_value = ""
            assert "item1" in screen._render_bottombar_fragments()
