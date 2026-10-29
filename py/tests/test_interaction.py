"""Interaction session: the default session, use_session isolation, and no registry leakage."""

import importlib
import threading

import pytest

s = importlib.import_module("bbsengine6.interaction")
c = importlib.import_module("bbsengine6.commands")


def test_default_session_is_used_when_none_is_set():
    assert s.current_session() is s._default_session


def test_default_session_is_stable():
    assert s.current_session() is s.current_session()


def test_use_session_switches_and_restores():
    before = s.current_session()
    mine = s.new_session(name="casino")
    with s.use_session(mine):
        assert s.current_session() is mine
    assert s.current_session() is before


def test_use_session_restores_after_exception():
    before = s.current_session()
    with pytest.raises(RuntimeError):
        with s.use_session(s.new_session(name="x")):
            raise RuntimeError("boom")
    assert s.current_session() is before


def test_nested_sessions_restore_in_order():
    outer = s.new_session(name="outer")
    inner = s.new_session(name="inner")
    with s.use_session(outer):
        with s.use_session(inner):
            assert s.current_session() is inner
        assert s.current_session() is outer


def test_registry_is_per_session():
    a = s.new_session(name="a")
    b = s.new_session(name="b")
    a.commands.register("hit", c.TIER_SESSION)
    assert a.commands.lookup("hit") is not None
    assert b.commands.lookup("hit") is None


def test_session_registry_does_not_leak_into_default():
    mine = s.new_session(name="casino")
    with s.use_session(mine):
        s.current_session().commands.register("snake", c.TIER_SESSION)
    assert s.current_session().commands.lookup("snake") is None


def test_session_registry_is_visible_only_inside_the_block():
    mine = s.new_session(name="casino")
    with s.use_session(mine):
        s.current_session().commands.register("stand", c.TIER_SESSION)
        assert s.current_session().commands.lookup("stand") is not None
    assert s.current_session().commands.lookup("stand") is None


def test_new_session_honours_replace_mode():
    mine = s.new_session(mode=c.MODE_REPLACE, name="casino")
    assert mine.commands.mode == c.MODE_REPLACE


def test_each_thread_sees_its_own_session():
    results = {}
    barrier = threading.Barrier(2)

    def worker(name):
        mine = s.new_session(name=name)
        with s.use_session(mine):
            barrier.wait()
            results[name] = s.current_session() is mine

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("t1", "t2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == {"t1": True, "t2": True}
