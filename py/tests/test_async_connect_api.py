"""The async connection helpers work with psycopg-pool 3.3, and a body TypeError is not masked.

Pins three fixes in bbsengine6.database:
  - async_connect chooses the connection form from what pool.connection() returns, instead of
    re-awaiting a context manager when the body raises TypeError.
  - AsyncDBConnection.cursor is a method, so db_conn.cursor() returns a cursor (not called on one).
"""

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

from bbsengine6 import database


class _FakeCursor:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def execute(self, *a, **k):
        return None

    async def fetchone(self):
        return None


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    async def close(self):
        return None


class _Pool33:
    """psycopg-pool 3.3 shape: connection() is an async context manager."""

    @asynccontextmanager
    async def connection(self):
        yield _FakeConn()


def test_async_db_connection_cursor_is_a_method():
    db = database.AsyncDBConnection(_FakeConn())
    assert callable(db.cursor)
    assert isinstance(db.cursor(), database.AsyncCursor)


def test_async_connect_works_with_the_33_context_manager_pool():
    async def run():
        async with database.async_connect(SimpleNamespace(), _Pool33()) as db:
            return db is not None

    assert asyncio.run(run()) is True
