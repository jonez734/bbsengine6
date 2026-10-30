"""
test_database_context_pool.py

``bbsengine6.database.context_pool`` yields the process's cached pool and never closes it.

Covers the lifetime rule the helper exists to enforce:
  - every scope for a database gets the same pool;
  - leaving a scope, normally or by an exception, does not close the pool;
  - the pool is still usable after a scope has ended;
  - the scope forwards its keyword arguments to ``getpool``.

Uses a fake pool, so no database is needed.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import database

pytestmark = pytest.mark.unit


def _args(name="zoid6test"):
    class _A:
        databasename = name

    return _A()


def test_scopes_share_one_pool():
    shared = MagicMock(name="pool")
    with patch.object(database, "getpool", return_value=shared):
        with database.context_pool(_args()) as first:
            pass
        with database.context_pool(_args()) as second:
            pass
    assert first is shared
    assert second is shared


def test_leaving_a_scope_does_not_close_the_pool():
    pool = MagicMock(name="pool")
    with patch.object(database, "getpool", return_value=pool):
        with database.context_pool(_args()):
            pass
    pool.close.assert_not_called()


def test_an_exception_inside_the_scope_does_not_close_the_pool():
    pool = MagicMock(name="pool")
    with patch.object(database, "getpool", return_value=pool):
        with pytest.raises(RuntimeError):
            with database.context_pool(_args()):
                raise RuntimeError("boom")
    pool.close.assert_not_called()


def test_the_pool_is_usable_after_a_scope_ends():
    pool = MagicMock(name="pool")
    with patch.object(database, "getpool", return_value=pool):
        with database.context_pool(_args()):
            pass
        with database.context_pool(_args()) as again:
            again.connection()
    pool.close.assert_not_called()
    pool.connection.assert_called_once()


def test_keyword_arguments_are_forwarded_to_getpool():
    with patch.object(database, "getpool", return_value=MagicMock()) as getpool:
        with database.context_pool(_args(), database="zoid6test"):
            pass
    assert getpool.call_args.kwargs.get("database") == "zoid6test"


def test_the_real_cache_is_not_closed_by_a_scope():
    """Against the real cache: a scope leaves the cached pool open and the same object is
    returned next time. Uses a stub pool installed in the cache, so no connection is opened."""
    stub = MagicMock(name="cached-pool", closed=False)
    key = "dbname=scope-test"
    with patch.object(database, "make_dsn", return_value=key), \
         patch.object(database, "ConnectionPool", return_value=stub), \
         patch.dict(database._pool_cache, {}, clear=True):
        with database.context_pool(_args("scope-test")) as first:
            pass
        with database.context_pool(_args("scope-test")) as second:
            pass
        assert first is stub and second is stub
        stub.close.assert_not_called()
        assert database._pool_cache[key] is stub
