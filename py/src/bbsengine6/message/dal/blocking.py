# bbsengine6/message/dal/blocking.py
#
# DAL functions for engine.__message_block. Pure Postgres I/O.

from __future__ import annotations

from typing import Any, List


def block(args: Any, blocker_moniker: str, blocked_moniker: str) -> None:
    """INSERT a row into ``engine.__message_block`` (idempotent)."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO engine.__message_block (blocker_moniker, blocked_moniker)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
            (blocker_moniker, blocked_moniker),
        )
        conn.commit()


def unblock(args: Any, blocker_moniker: str, blocked_moniker: str) -> None:
    """DELETE a row from ``engine.__message_block``."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                DELETE FROM engine.__message_block
                WHERE blocker_moniker = %s AND blocked_moniker = %s
                """,
            (blocker_moniker, blocked_moniker),
        )
        conn.commit()


def is_blocked(args: Any, blocker_moniker: str, blocked_moniker: str) -> bool:
    """Return True if a ``blocker`` row exists for the pair."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT 1 FROM engine.__message_block
                WHERE blocker_moniker = %s AND blocked_moniker = %s
                """,
            (blocker_moniker, blocked_moniker),
        )
        return cur.fetchone() is not None


def list_blocked_by(args: Any, moniker: str) -> List[str]:
    """Return the ``blocker_moniker``s that have blocked ``moniker``.

    Semantically the inverse of ``is_blocked``: for each row in
    ``engine.__message_block`` where ``blocked_moniker = moniker``,
    return the corresponding ``blocker_moniker``.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT blocker_moniker FROM engine.__message_block
                WHERE blocked_moniker = %s
                """,
            (moniker,),
        )
        return [row[0] for row in cur.fetchall()]
