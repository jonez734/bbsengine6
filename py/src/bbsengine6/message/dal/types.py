# bbsengine6/message/dal/types.py
#
# DAL write helpers for engine.__message_type. Read helpers live in
# ``bbsengine6.message.dal.ratelimit``. Pure Postgres I/O.

from __future__ import annotations

from typing import Any, Dict, List


def upsert(
    args: Any,
    type_name: str,
    description: str,
    rate_limit_per_hour: int,
    requires_approval: bool,
) -> None:
    """INSERT-or-UPDATE an ``engine.__message_type`` row."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO engine.__message_type
                    (type_name, description, rate_limit_per_hour,
                     requires_approval, datemodified)
                VALUES (%s, %s, %s, %s, now())
                ON CONFLICT (type_name) DO UPDATE
                SET description = EXCLUDED.description,
                    rate_limit_per_hour = EXCLUDED.rate_limit_per_hour,
                    requires_approval = EXCLUDED.requires_approval,
                    datemodified = now()
                """,
            (
                type_name,
                description,
                int(rate_limit_per_hour),
                bool(requires_approval),
            ),
        )
        conn.commit()


def set_rate_limit(args: Any, type_name: str, limit: int) -> None:
    """Runtime adjustment of the per-hour rate limit for a type.

    Creates the type row if it does not already exist (with the new
    limit and an empty description).
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO engine.__message_type
                    (type_name, description, rate_limit_per_hour, datemodified)
                VALUES (%s, %s, %s, now())
                ON CONFLICT (type_name) DO UPDATE
                SET rate_limit_per_hour = EXCLUDED.rate_limit_per_hour,
                    datemodified = now()
                """,
            (type_name, "", int(limit)),
        )
        conn.commit()


def list_all(args: Any) -> List[Dict[str, Any]]:
    """Return every registered ``engine.__message_type`` row."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT type_name, description, rate_limit_per_hour,
                       requires_approval, datemodified
                FROM engine.__message_type
                ORDER BY type_name
                """
        )
        rows = cur.fetchall()
        return [
            {
                "type_name": row[0],
                "description": row[1],
                "rate_limit_per_hour": row[2],
                "requires_approval": row[3],
                "datemodified": row[4],
            }
            for row in rows
        ]
