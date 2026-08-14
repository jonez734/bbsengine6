"""
test_check_notifications_args_pool.py

Regression test for the bug where projup (and other tools using
io.inputchar) connected to a hardcoded `bbsengine6` database instead
of honoring the user's --databasename / pool.

The polling loop in io.getch._check_notifications(moniker, **kwargs) must
forward `args` and `pool` from the caller down to
bbsengine6.message.get_unread_count, so that:

  1. No new pool is created with the env-var default db.
  2. The user's pool-1 is reused for the unread-count query.
"""

import pytest

pytestmark = pytest.mark.unit


class _Args:
    def __init__(self, databasename: str = "zoidbo") -> None:
        self.databasename = databasename
        self.database = databasename
        self.debug = False


class _Pool:
    name = "pool-1"


class TestCheckNotificationsForwardsArgs:
    def test_forwards_args_and_pool_to_get_unread_count(self, monkeypatch):
        from bbsengine6 import message
        from bbsengine6.io.getch import _check_notifications
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"

        captured = []

        def fake_get_unread_count(moniker, database=None, *, args=None, pool=None, conn=None):
            captured.append(
                {"moniker": moniker, "database": database, "args": args, "pool": pool, "conn": conn}
            )
            return 7

        monkeypatch.setattr(message, "get_unread_count", fake_get_unread_count)
        message.clear_local_unread_cache()

        args = _Args("zoidbo")
        pool = _Pool()

        has, count = _check_notifications("JAM!", args=args, pool=pool)

        assert has is True
        assert count == 7
        assert len(captured) == 1
        call = captured[0]
        assert call["moniker"] == "JAM!"
        assert call["args"] is args
        assert call["pool"] is pool
        assert call["conn"] is None

    def test_warm_cache_skips_db_call(self, monkeypatch):
        from bbsengine6 import message
        from bbsengine6.io.getch import _check_notifications
        from bbsengine6.member import _threadlocal

        _threadlocal.moniker = "JAM!"

        called = []

        def fake_get_unread_count(moniker, database=None, *, args=None, pool=None, conn=None):
            called.append(moniker)
            return 0

        monkeypatch.setattr(message, "get_unread_count", fake_get_unread_count)
        message.set_local_unread_count("JAM!", 3)

        has, count = _check_notifications("JAM!", args=_Args(), pool=_Pool())

        assert has is True
        assert count == 3
        assert called == [], "warm cache should not hit the DB"


class TestResolveDbFallsBackToArgs:
    def test_uses_args_databasename_when_no_explicit_db(self):
        from bbsengine6.message import lib as message_lib

        args = _Args("zoidbo")
        assert message_lib._resolve_db(None, args) == "zoidbo"

    def test_uses_args_database_attr_as_fallback(self):
        from bbsengine6.message import lib as message_lib

        class AltArgs:
            databasename = None
            database = "altdb"

        assert message_lib._resolve_db(None, AltArgs()) == "altdb"

    def test_explicit_database_overrides_args(self):
        from bbsengine6.message import lib as message_lib

        args = _Args("zoidbo")
        assert message_lib._resolve_db("override", args) == "override"

    def test_falls_back_to_default_when_nothing_supplied(self, monkeypatch):
        from bbsengine6.message import lib as message_lib

        monkeypatch.delenv("BBSENGINE6_DBNAME", raising=False)
        assert message_lib._resolve_db(None, None) == "zoid6"

    def test_falls_back_to_env_var_when_args_has_no_db(self, monkeypatch):
        from bbsengine6.message import lib as message_lib

        monkeypatch.setenv("BBSENGINE6_DBNAME", "envdb")

        class NoDbArgs:
            databasename = None
            database = None

        assert message_lib._resolve_db(None, NoDbArgs()) == "envdb"


class TestGetUnreadCountAcceptsArgsAndPool:
    def test_pool_is_reused_no_new_getpool_call(self, monkeypatch):
        from bbsengine6 import message

        class FakePool:
            def __init__(self):
                self.connections = 0
                self.last_sql = None
                self.last_params = None

            def connection(self):
                self.connections += 1
                outer = self

                class Conn:
                    def cursor(self_inner):
                        class Cur:
                            def __enter__(s): return s
                            def __exit__(s, *a): return False
                            def execute(s, sql, params):
                                outer.last_sql = sql
                                outer.last_params = params
                            def fetchone(s):
                                return [11]
                        return Cur()

                class Ctx:
                    def __enter__(s): return Conn()
                    def __exit__(s, *a): return False

                return Ctx()

        getpool_called = []

        def fake_getpool(args, **kwargs):
            getpool_called.append((args, kwargs))
            return None  # if we got here, the test fails

        monkeypatch.setattr(message, "getpool", fake_getpool)

        pool = FakePool()
        count = message.get_unread_count("JAM!", pool=pool)

        assert count == 11
        assert pool.connections == 1, "expected exactly one connection checkout"
        assert "engine.__message_recipient" in pool.last_sql
        assert pool.last_params == ("JAM!",)
        assert getpool_called == [], "should not call getpool when pool is given"

    def test_conn_is_used_directly(self, monkeypatch):
        from bbsengine6 import message

        class Cur:
            def __enter__(s): return s
            def __exit__(s, *a): return False
            def execute(s, sql, params): pass
            def fetchone(s): return [9]

        class Conn:
            def cursor(s): return Cur()

        getpool_called = []

        monkeypatch.setattr(
            message,
            "getpool",
            lambda *a, **k: getpool_called.append((a, k)) or None,
        )

        count = message.get_unread_count("JAM!", conn=Conn())
        assert count == 9
        assert getpool_called == [], "should not call getpool when conn is given"

    def test_disabled_returns_zero_without_db(self, monkeypatch):
        from bbsengine6 import message

        message.disable()
        try:
            assert message.get_unread_count("JAM!") == 0
        finally:
            message.enable()
