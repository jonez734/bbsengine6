"""
test_check_notifications_registry_fallback.py

When the caller of io.getch does not pass args or pool to
_check_notifications (the inputchoice prompt path), the unread-count query
must read the session's bottombar registry, not the default database.

Before the fix, args and pool were forwarded as None, so
message.get_unread_count fell back to the default database ("zoid6") with no
login user, and failed with "permission denied for schema engine".
"""

import importlib

import pytest

pytestmark = pytest.mark.unit


def _getch():
    # bbsengine6.io exports a getch() function, which shadows the module.
    return importlib.import_module("bbsengine6.io.getch")


class _Args:
    def __init__(self, databasename="zoid6test", databaseuser="jam"):
        self.databasename = databasename
        self.database = databasename
        self.databaseuser = databaseuser
        self.debug = False


class _Pool:
    name = "session-pool"


class _Registry:
    def __init__(self, args=None, pool=None):
        self.args = args
        self.pool = pool


def _capture_unread(monkeypatch):
    from bbsengine6 import message

    captured = []

    def fake(moniker, database=None, *, args=None, pool=None, conn=None):
        captured.append({"args": args, "pool": pool, "conn": conn})
        return 4

    monkeypatch.setattr(message, "get_unread_count", fake)
    message.clear_local_unread_cache()
    return captured


class TestRegistryFallback:
    def test_uses_registry_args_and_pool_when_caller_passes_none(self, monkeypatch):
        getch = _getch()
        from bbsengine6 import bottombar
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"
        captured = _capture_unread(monkeypatch)
        reg_args, reg_pool = _Args(), _Pool()
        monkeypatch.setattr(
            bottombar, "_resolve_registry", lambda name=None: _Registry(reg_args, reg_pool)
        )

        has, count = getch._check_notifications("JAM!")

        assert count == 4
        assert len(captured) == 1
        assert captured[0]["args"] is reg_args
        assert captured[0]["pool"] is reg_pool

    def test_explicit_args_and_pool_win_over_registry(self, monkeypatch):
        getch = _getch()
        from bbsengine6 import bottombar
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"
        captured = _capture_unread(monkeypatch)
        monkeypatch.setattr(
            bottombar,
            "_resolve_registry",
            lambda name=None: _Registry(_Args("other"), _Pool()),
        )
        explicit_args, explicit_pool = _Args("zoid6test"), _Pool()

        getch._check_notifications("JAM!", args=explicit_args, pool=explicit_pool)

        assert captured[0]["args"] is explicit_args
        assert captured[0]["pool"] is explicit_pool

    def test_partial_kwargs_fill_only_the_missing_piece(self, monkeypatch):
        getch = _getch()
        from bbsengine6 import bottombar
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"
        captured = _capture_unread(monkeypatch)
        reg_pool = _Pool()
        monkeypatch.setattr(
            bottombar,
            "_resolve_registry",
            lambda name=None: _Registry(_Args("registry"), reg_pool),
        )
        explicit_args = _Args("explicit")

        getch._check_notifications("JAM!", args=explicit_args)

        assert captured[0]["args"] is explicit_args
        assert captured[0]["pool"] is reg_pool

    def test_empty_registry_passes_none_without_error(self, monkeypatch):
        getch = _getch()
        from bbsengine6 import bottombar
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"
        captured = _capture_unread(monkeypatch)
        monkeypatch.setattr(
            bottombar, "_resolve_registry", lambda name=None: _Registry(None, None)
        )

        has, count = getch._check_notifications("JAM!")

        assert captured[0]["args"] is None
        assert captured[0]["pool"] is None
        assert count == 4

    def test_warm_cache_skips_registry_lookup_and_db(self, monkeypatch):
        getch = _getch()
        from bbsengine6 import bottombar, message
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"
        captured = _capture_unread(monkeypatch)
        message.set_local_unread_count("JAM!", 2)
        looked_up = []
        monkeypatch.setattr(
            bottombar,
            "_resolve_registry",
            lambda name=None: looked_up.append(name) or _Registry(_Args(), _Pool()),
        )

        has, count = getch._check_notifications("JAM!")

        assert count == 2
        assert captured == []
