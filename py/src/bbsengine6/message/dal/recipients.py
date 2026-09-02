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
