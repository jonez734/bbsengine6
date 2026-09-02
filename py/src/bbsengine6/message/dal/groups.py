# bbsengine6/message/dal/groups.py
#
# DAL functions for engine.__message_group and
# engine.__message_group_member. Pure Postgres I/O.

from __future__ import annotations

from typing import Any, Dict, List, Optional


def create(args: Any, name: str, createdby: Optional[str], description: Optional[str]) -> int:
    """INSERT a new ``engine.__message_group`` row and return its id."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO engine.__message_group (name, description, createdby)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
            (name, description, createdby),
        )
        group_id = cur.fetchone()[0]
        conn.commit()
        return group_id


def add_member(
    args: Any,
    group_id: int,
    member_moniker: str,
    addedby: Optional[str],
) -> None:
    """INSERT a row into ``engine.__message_group_member`` (idempotent)."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engine.__message_group_member (group_id, member_moniker, addedby)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (group_id, member_moniker, addedby),
        )
        conn.commit()


def remove_member(args: Any, group_id: int, member_moniker: str) -> bool:
    """DELETE a ``engine.__message_group_member`` row.

    Returns True if a row was removed, False otherwise.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                DELETE FROM engine.__message_group_member
                WHERE group_id = %s AND member_moniker = %s
                """,
            (group_id, member_moniker),
        )
        removed = cur.rowcount > 0
        conn.commit()
        return removed


def list_members(args: Any, group_id: int) -> List[str]:
    """SELECT ``member_moniker`` rows for a group."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT member_moniker FROM engine.__message_group_member
                WHERE group_id = %s
                """,
            (group_id,),
        )
        return [row[0] for row in cur.fetchall()]


def list_user_groups(args: Any, moniker: str) -> List[Dict[str, Any]]:
    """SELECT every ``engine.__message_group`` a user belongs to."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT g.id, g.name, g.description, g.datecreated
                FROM engine.__message_group g
                JOIN engine.__message_group_member m ON m.group_id = g.id
                WHERE m.member_moniker = %s
                """,
            (moniker,),
        )
        rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "datecreated": row[3],
            }
            for row in rows
        ]
