# bbsengine6/message/dal/_pool.py
#
# Shared helpers for the bbsengine6.message DAL: CONN_POOL_PATTERN
# connection context and a generic information_schema probe.
#
# Mirrors the casino DAL helper shape (see
# ``casino/src/casino/dal/bet.py`` ``_connect_ctx``).

from __future__ import annotations

from typing import Any


def _connect_ctx(args: Any, pool: Any):
    """Return a context manager for a database connection.

    CONN_POOL_PATTERN helper: when ``pool`` is supplied the
    connection is borrowed from the caller's pool; otherwise the
    legacy ``bbsengine6.database.connect(args)`` fallback is used.
    """
    from bbsengine6 import database

    if pool is None:
        return database.connect(args)
    return database.connect(args, pool=pool)


def table_exists(cur: Any, schema: str, table: str) -> bool:
    """Probe ``schema.table`` existence on an already-open cursor.

    Runs a single SELECT against ``information_schema.tables`` and
    returns True if a row matches. Never raises -- returns False on
    any exception so a probe failure cannot mask the caller's intent.

    Doing the probe on the caller's existing cursor keeps the
    ``bbsengine6.message`` package free of any ``psycopg`` import.
    """
    try:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = %s AND table_name = %s",
            (schema, table),
        )
    except Exception:
        return False
    try:
        return cur.fetchone() is not None
    except Exception:
        return False
