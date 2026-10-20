# bbsengine6/message/dal/recipients.py
#
# DAL helper for ``engine.__member`` and ``engine.__message_group``
# lookups during recipient expansion. Pure Postgres I/O.

from __future__ import annotations

from typing import Any, List


def list_all_approved_member_monikers(args: Any) -> List[str]:
    """Return the monikers of every approved ``engine.__member``.

    Used to expand the ``@everyone`` recipient token.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute("SELECT moniker FROM engine.__member WHERE approved = TRUE")
        return [row[0] for row in cur.fetchall()]


def get_group_id_by_name(args: Any, name: str) -> int:
    """Return the id of ``engine.__message_group`` for ``name``, or
    ``-1`` if no such group exists.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM engine.__message_group WHERE name = %s",
            (name,),
        )
        row = cur.fetchone()
        return row[0] if row else -1


def source_may_address_group(args: Any, source: str, group_name: str) -> bool:
    """True if named ``source`` is registered for a prefix of ``group_name``.

    A registration matches when ``group_name`` equals the registered
    ``group_prefix`` or starts with it followed by ``:`` (so the prefix
    ``table`` covers ``table:jam``). Unregistered sources match nothing.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM engine.__message_source
            WHERE source = %s
              AND (%s = group_prefix OR %s LIKE group_prefix || ':%%')
            LIMIT 1
            """,
            (source, group_name, group_name),
        )
        return cur.fetchone() is not None


def register_source(args: Any, source: str, group_prefix: str, description: str | None = None) -> None:
    """Register ``source`` to address groups under ``group_prefix`` (idempotent)."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engine.__message_source (source, group_prefix, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (source, group_prefix) DO NOTHING
            """,
            (source, group_prefix, description),
        )
        conn.commit()


def unregister_source(args: Any, source: str, group_prefix: str | None = None) -> None:
    """Remove a registration. With no prefix, remove every prefix for ``source``."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        if group_prefix is None:
            cur.execute("DELETE FROM engine.__message_source WHERE source = %s", (source,))
        else:
            cur.execute(
                "DELETE FROM engine.__message_source WHERE source = %s AND group_prefix = %s",
                (source, group_prefix),
            )
        conn.commit()
