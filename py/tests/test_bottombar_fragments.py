"""Object fragments: lazy init on first render, failure reported once and skipped, shutdown on leave/exit."""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar as bb


class Frag:
    def __init__(self, text="x", init_raises=False, shutdown_raises=False):
        self.text = text
        self.init_calls = 0
        self.shutdown_calls = 0
        self.render_calls = 0
        self._init_raises = init_raises
        self._shutdown_raises = shutdown_raises

    def init(self, **kwargs):
        self.init_calls += 1
        if self._init_raises:
            raise RuntimeError("init boom")

    def render(self, **kwargs):
        self.render_calls += 1
        return self.text

    def shutdown(self):
        self.shutdown_calls += 1
        if self._shutdown_raises:
            raise RuntimeError("shutdown boom")


@pytest.fixture(autouse=True)
def _clean_state():
    bb._FRAGMENT_STATE.clear()
    yield
    bb._FRAGMENT_STATE.clear()


@pytest.mark.unit
def test_register_does_not_call_init():
    reg = bb.FragmentRegistry("t")
    f = Frag()
    reg.register(f)
    assert f.init_calls == 0


@pytest.mark.unit
def test_first_render_inits_then_later_renders_do_not():
    reg = bb.FragmentRegistry("t")
    f = Frag("hi")
    reg.register(f)
    with patch.object(bb, "_get_notification_status", return_value=""):
        assert reg.render() == "hi"
        assert reg.render() == "hi"
    assert f.init_calls == 1
    assert f.render_calls == 2


@pytest.mark.unit
def test_failed_init_is_reported_once_and_skipped():
    reg = bb.FragmentRegistry("t")
    f = Frag("hi", init_raises=True)
    reg.register(f)
    with patch.object(bb, "_get_notification_status", return_value=""), \
         patch.object(bb, "echo_traceback") as tb:
        assert reg.render() == ""
        assert reg.render() == ""
    assert f.init_calls == 1
    assert f.render_calls == 0
    assert tb.call_count == 1


@pytest.mark.unit
def test_unregister_shuts_down_an_initialized_fragment():
    reg = bb.FragmentRegistry("t")
    f = Frag()
    reg.register(f)
    with patch.object(bb, "_get_notification_status", return_value=""):
        reg.render()
    assert reg.unregister(f) is True
    assert f.shutdown_calls == 1


@pytest.mark.unit
def test_unregister_does_not_shut_down_a_never_initialized_fragment():
    reg = bb.FragmentRegistry("t")
    f = Frag()
    reg.register(f)
    reg.unregister(f)
    assert f.shutdown_calls == 0


@pytest.mark.unit
def test_clear_shuts_down_every_initialized_fragment():
    reg = bb.FragmentRegistry("t")
    a, b = Frag("a"), Frag("b")
    reg.register(a)
    reg.register(b)
    with patch.object(bb, "_get_notification_status", return_value=""):
        reg.render()
    reg.clear()
    assert a.shutdown_calls == 1 and b.shutdown_calls == 1


@pytest.mark.unit
def test_bottombar_shutdown_runs_fragment_teardown_without_screen_init():
    reg = bb.FragmentRegistry("t")
    f = Frag()
    reg.register(f)
    with patch.object(bb, "_get_notification_status", return_value=""):
        reg.render()
    bb._initialized = False
    with patch.object(bb, "_REGISTRY_CACHE", {"t": reg}):
        bb.shutdown()
    assert f.shutdown_calls == 1


@pytest.mark.unit
def test_a_raising_shutdown_does_not_stop_the_others_or_the_exit():
    reg = bb.FragmentRegistry("t")
    bad = Frag("bad", shutdown_raises=True)
    good = Frag("good")
    reg.register(bad)
    reg.register(good)
    with patch.object(bb, "_get_notification_status", return_value=""), \
         patch.object(bb, "echo_traceback"):
        reg.render()
        reg.clear()
    assert good.shutdown_calls == 1


@pytest.mark.unit
def test_plain_callables_and_strings_are_unchanged():
    reg = bb.FragmentRegistry("t")
    reg.register("static")
    reg.register(lambda **k: "dyn")
    with patch.object(bb, "_get_notification_status", return_value=""):
        assert reg.render() == "static | dyn"
