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
def _clean_bottombar_state():
    """Save and restore bottombar module state around each test.

    Resets the default registry, the named-registry cache, the
    `_DEFAULT_REGISTRY` global, and the per-connection ContextVar
    so tests don't bleed.
    """
    reg = default_registry()
    saved_items = list(reg.items)
    saved_args = reg.args
    saved_player = reg.player
    saved_pool = reg.pool
    reg.clear()
    reg.args = None
    reg.player = None
    reg.pool = None

    saved_cache = dict(bottombar._REGISTRY_CACHE)
    saved_default = bottombar._DEFAULT_REGISTRY
    bottombar._REGISTRY_CACHE.clear()
    bottombar._DEFAULT_REGISTRY = None
    token = bottombar._active_registry.set(None)

    yield

    bottombar._active_registry.reset(token)
    bottombar._REGISTRY_CACHE.clear()
    bottombar._DEFAULT_REGISTRY = None
    bottombar._REGISTRY_CACHE.update(saved_cache)
    bottombar._DEFAULT_REGISTRY = saved_default

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


# ---------------------------------------------------------------------------
# Phase 4a: registry_for(name) factory
# ---------------------------------------------------------------------------


class TestRegistryFor:
    def test_registry_for_creates_named_registry(self):
        from bbsengine6.bottombar import registry_for

        reg = registry_for("empyre")
        assert isinstance(reg, FragmentRegistry)
        assert reg.name == "empyre"

    def test_registry_for_caches(self):
        from bbsengine6.bottombar import registry_for

        a = registry_for("empyre")
        b = registry_for("empyre")
        assert a is b

    def test_registry_for_different_names(self):
        from bbsengine6.bottombar import registry_for

        a = registry_for("empyre")
        b = registry_for("casino")
        assert a is not b
        assert a.name == "empyre"
        assert b.name == "casino"

    def test_registry_for_default_returns_default_registry(self):
        from bbsengine6.bottombar import registry_for

        assert registry_for("default") is default_registry()

    def test_registry_for_does_not_pollute_default(self):
        from bbsengine6.bottombar import registry_for

        registry_for("empyre").register("empyre-only")
        assert "empyre-only" not in default_registry()
        assert "empyre-only" in registry_for("empyre")

    def test_registry_for_bypasses_contextvar(self):
        from bbsengine6.bottombar import (
            registry_for,
            set_active_registry,
            reset_active_registry,
        )

        sentinel = FragmentRegistry(name="sentinel")
        token = set_active_registry(sentinel)
        try:
            reg = registry_for("empyre")
            assert reg is not sentinel
            assert reg.name == "empyre"
        finally:
            reset_active_registry(token)

    def test_registry_for_independent_state(self):
        from bbsengine6.bottombar import registry_for

        empyre = registry_for("empyre")
        casino = registry_for("casino")
        empyre.register("e1")
        casino.register("c1")
        assert "e1" in empyre
        assert "e1" not in casino
        assert "c1" in casino
        assert "c1" not in empyre


# ---------------------------------------------------------------------------
# Phase 4a: set_context_for and render_for
# ---------------------------------------------------------------------------


class TestSetContextForAndRenderFor:
    def test_set_context_for_stashes_player(self):
        from bbsengine6.bottombar import set_context_for, registry_for

        sentinel = object()
        set_context_for("empyre", player=sentinel)
        assert registry_for("empyre").player is sentinel

    def test_set_context_for_stashes_args_and_pool(self):
        from bbsengine6.bottombar import set_context_for, registry_for

        sentinel_args = object()
        sentinel_pool = object()
        set_context_for("empyre", args=sentinel_args, pool=sentinel_pool)
        reg = registry_for("empyre")
        assert reg.args is sentinel_args
        assert reg.pool is sentinel_pool

    def test_render_for_uses_named_registry(self):
        from bbsengine6.bottombar import render_for, registry_for

        registry_for("empyre").register("e-frag")
        assert "e-frag" in render_for("empyre")
        assert "e-frag" not in render_for("casino")

    def test_render_for_passes_named_context(self):
        from bbsengine6.bottombar import render_for, set_context_for

        captured = {}

        def frag(**kw):
            captured.update(kw)
            return "ok"

        set_context_for("empyre", player="sentinel-player")
        registry_for = __import__(
            "bbsengine6.bottombar", fromlist=["registry_for"]
        ).registry_for
        registry_for("empyre").register(frag)
        render_for("empyre")
        assert captured.get("player") == "sentinel-player"

    def test_render_for_empty_returns_empty(self):
        from bbsengine6.bottombar import render_for

        assert render_for("empyre") == ""


# ---------------------------------------------------------------------------
# Phase 4a: ContextVar routing
# ---------------------------------------------------------------------------


class TestContextVarRouting:
    def test_default_routes_to_default_registry(self):
        from bbsengine6.bottombar import (
            setbottombar,
        )

        sentinel_args = object()
        with patch("bbsengine6.bottombar._render_bottombar"):
            setbottombar(sentinel_args, "left")
        assert default_registry().args is sentinel_args

    def test_active_registry_routes_setbottombar(self):
        from bbsengine6.bottombar import (
            reset_active_registry,
            set_active_registry,
            setbottombar,
        )

        sentinel = FragmentRegistry(name="per-conn")
        sentinel_args = object()
        token = set_active_registry(sentinel)
        try:
            with patch("bbsengine6.bottombar._render_bottombar"):
                setbottombar(sentinel_args, "left")
            assert sentinel.args is sentinel_args
            assert default_registry().args is None
        finally:
            reset_active_registry(token)

    def test_active_registry_routes_register(self):
        from bbsengine6.bottombar import (
            register_bottombar_fragment,
            reset_active_registry,
            set_active_registry,
            unregister_bottombar_fragment,
        )

        sentinel = FragmentRegistry(name="per-conn")
        token = set_active_registry(sentinel)
        try:
            register_bottombar_fragment("pinned")
            assert "pinned" in sentinel
            assert "pinned" not in default_registry()
            unregister_bottombar_fragment("pinned")
            assert "pinned" not in sentinel
        finally:
            reset_active_registry(token)

    def test_active_registry_routes_clear(self):
        from bbsengine6.bottombar import (
            clear_bottombar_fragments,
            reset_active_registry,
            set_active_registry,
        )

        sentinel = FragmentRegistry(name="per-conn")
        sentinel.register("keep-default")
        default_registry().register("would-be-cleared")
        token = set_active_registry(sentinel)
        try:
            clear_bottombar_fragments()
            assert len(sentinel) == 0
            assert "would-be-cleared" in default_registry()
        finally:
            reset_active_registry(token)

    def test_reset_token_restores_default(self):
        from bbsengine6.bottombar import (
            reset_active_registry,
            set_active_registry,
            setbottombar,
        )

        sentinel = FragmentRegistry(name="per-conn")
        token = set_active_registry(sentinel)
        with patch("bbsengine6.bottombar._render_bottombar"):
            setbottombar(None, "while-set")
        assert sentinel.args is None
        reset_active_registry(token)
        sentinel_args = object()
        with patch("bbsengine6.bottombar._render_bottombar"):
            setbottombar(sentinel_args, "after-reset")
        assert default_registry().args is sentinel_args
        assert sentinel.args is None

    def test_explicit_name_resolves_to_named_registry(self):
        from bbsengine6.bottombar import (
            reset_active_registry,
            set_active_registry,
            set_context_for,
        )

        sentinel = FragmentRegistry(name="per-conn")
        token = set_active_registry(sentinel)
        try:
            sentinel_player = object()
            set_context_for("empyre", player=sentinel_player)
            empyre = __import__(
                "bbsengine6.bottombar", fromlist=["registry_for"]
            ).registry_for("empyre")
            assert empyre.player is sentinel_player
            assert sentinel.player is None
        finally:
            reset_active_registry(token)

    def test_active_registry_none_falls_back_to_default(self):
        from bbsengine6.bottombar import (
            reset_active_registry,
            set_active_registry,
            setbottombar,
        )

        token = set_active_registry(None)
        try:
            sentinel_args = object()
            with patch("bbsengine6.bottombar._render_bottombar"):
                setbottombar(sentinel_args, "left")
            assert default_registry().args is sentinel_args
        finally:
            reset_active_registry(token)


# ---------------------------------------------------------------------------
# Phase 4a: io.screen shim honors the ContextVar
# ---------------------------------------------------------------------------


class TestScreenShimContextVarRouting:
    def test_setbottombar_uses_default_when_no_contextvar(self):
        from bbsengine6.io import screen

        screen.register_bottombar_fragment("door-frag")
        with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
            screen.setbottombar("left")
            rendered = mock_update.call_args[0][0]
            assert "door-frag" in rendered

    def test_setbottombar_uses_active_registry_when_set(self):
        from bbsengine6.bottombar import (
            FragmentRegistry as _FR,
            reset_active_registry,
            set_active_registry,
        )
        from bbsengine6.io import screen

        per_conn = _FR(name="per-conn")
        per_conn.register("per-conn-frag")
        default_registry().register("door-frag")
        token = set_active_registry(per_conn)
        try:
            with patch("bbsengine6.io.screen.updatebottombar") as mock_update:
                screen.setbottombar("left")
                rendered = mock_update.call_args[0][0]
                assert "per-conn-frag" in rendered
                assert "door-frag" not in rendered
        finally:
            reset_active_registry(token)

    def test_register_uses_active_registry(self):
        from bbsengine6.bottombar import (
            FragmentRegistry as _FR,
            reset_active_registry,
            set_active_registry,
        )
        from bbsengine6.io import screen

        per_conn = _FR(name="per-conn")
        token = set_active_registry(per_conn)
        try:
            screen.register_bottombar_fragment("sc-frag")
            assert "sc-frag" in per_conn
            assert "sc-frag" not in default_registry()
        finally:
            reset_active_registry(token)

    def test_unregister_uses_active_registry(self):
        from bbsengine6.bottombar import (
            FragmentRegistry as _FR,
            reset_active_registry,
            set_active_registry,
        )
        from bbsengine6.io import screen

        per_conn = _FR(name="per-conn")
        per_conn.register("sc-frag")
        default_registry().register("sc-frag")
        token = set_active_registry(per_conn)
        try:
            screen.unregister_bottombar_fragment("sc-frag")
            assert "sc-frag" not in per_conn
            assert "sc-frag" in default_registry()
        finally:
            reset_active_registry(token)

    def test_render_bottombar_fragments_uses_active_registry(self):
        from bbsengine6.bottombar import (
            FragmentRegistry as _FR,
            reset_active_registry,
            set_active_registry,
        )
        from bbsengine6.io import screen

        per_conn = _FR(name="per-conn")
        per_conn.register("per-conn-render")
        default_registry().register("door-render")
        token = set_active_registry(per_conn)
        try:
            with patch("bbsengine6.io.screen.get_notification_status") as mock_n:
                mock_n.return_value = ""
                rendered = screen._render_bottombar_fragments()
                assert "per-conn-render" in rendered
                assert "door-render" not in rendered
        finally:
            reset_active_registry(token)


# ---------------------------------------------------------------------------
# Regression: bbsengine6.screen and bbsengine6.io.screen must be the same
# module object. Pre-registration in bbsengine6/io/__init__.py pins the
# aliasing contract.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestScreenModuleUnification:
    """bbsengine6.screen and bbsengine6.io.screen resolve to one module.

    The same dual-module-import bug documented for bbsengine6.session in
    casino/tests/test_main_dispatch.py:183-193 affected screen too:
    pytest can produce two distinct module objects for the same logical
    path, so mock.patch("bbsengine6.io.screen.X") and
    mock.patch("bbsengine6.screen.X") would land on different bindings
    and not stick for callers that imported the other path.
    """

    def test_bbsengine6_screen_is_bbsengine6_io_screen(self):
        import bbsengine6.screen as canonical
        import bbsengine6.io.screen as legacy
        assert canonical is legacy
        assert sys.modules["bbsengine6.io.screen"] is canonical
        assert sys.modules["bbsengine6.screen"] is canonical

    def test_from_import_resolves_against_canonical(self):
        from bbsengine6.io.screen import (
            setarea,
            setbottombar,
            init,
            register_bottombar_fragment,
            unregister_bottombar_fragment,
            _render_bottombar_fragments,
            bottombarstack,
        )
        import bbsengine6.screen as canonical
        # Every legacy import resolves to the canonical symbol.
        assert setarea is canonical.setarea
        assert setbottombar is canonical.setbottombar
        assert init is canonical.init
        assert register_bottombar_fragment is canonical.register_bottombar_fragment
        assert unregister_bottombar_fragment is canonical.unregister_bottombar_fragment
        assert _render_bottombar_fragments is canonical._render_bottombar_fragments
        assert bottombarstack is canonical.bottombarstack

    def test_patch_on_canonical_visible_via_legacy_path(self):
        import bbsengine6
        import bbsengine6.screen as canonical
        from bbsengine6.io import screen as legacy  # noqa: F401

        sentinel = object()
        with patch.object(canonical, "setarea", sentinel):
            assert legacy.setarea is sentinel
            assert bbsengine6.io.screen.setarea is sentinel

    def test_patch_on_legacy_visible_via_canonical_path(self):
        import bbsengine6
        from bbsengine6.io import screen as legacy

        sentinel = object()
        with patch.object(legacy, "setarea", sentinel):
            assert bbsengine6.screen.setarea is sentinel
            assert sys.modules["bbsengine6.io.screen"].setarea is sentinel

    def test_patch_dotted_string_path_lands_on_canonical(self):
        # Patching via the dotted string "bbsengine6.io.screen.setarea"
        # must reach the same module attribute as patching via
        # "bbsengine6.screen.setarea". Without unification these would
        # be different module objects.
        import bbsengine6
        sentinel = object()
        with patch("bbsengine6.io.screen.setarea", sentinel):
            assert bbsengine6.screen.setarea is sentinel
        with patch("bbsengine6.screen.setarea", sentinel):
            assert bbsengine6.io.screen.setarea is sentinel

    def test_setarea_propagates_exceptions(self):
        """setarea is a direct delegation, not a try/except wrapper.

        Regression: the previous bbsengine6.screen.setarea wrapper
        silently returned None on any exception, hiding bugs in legacy
        callers. The current implementation raises.
        """
        import bbsengine6.screen as canonical

        # Sanity: setarea and setbottombar are distinct callable objects,
        # but setarea delegates to setbottombar (so patching the
        # underlying setbottombar must affect setarea's behavior).
        assert callable(canonical.setarea)
        assert callable(canonical.setbottombar)

        with patch(
            "bbsengine6.screen.setbottombar",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(RuntimeError):
                canonical.setarea("left", "right")

    def test_setarea_emits_deprecation_warning(self):
        """setarea is on the deprecation path; warn on every call."""
        import bbsengine6.screen as canonical
        import warnings

        with patch("bbsengine6.screen.setbottombar", return_value=None):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                canonical.setarea("left", "right")
        deprecation = [
            w for w in caught if issubclass(w.category, DeprecationWarning)
        ]
        assert deprecation, "expected DeprecationWarning from setarea"
        assert "bbsengine6.bottombar" in str(deprecation[0].message)
