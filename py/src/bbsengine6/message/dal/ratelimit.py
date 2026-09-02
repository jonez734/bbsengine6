# bbsengine6/message/dal/ratelimit.py
#
# DAL functions for engine.__message_rate_limit and the read side
# of engine.__message_type. Pure Postgres I/O. Type writes live in
# ``bbsengine6.message.dal.types``.

from __future__ import annotations

from datetime import datetime
from typing import Any, Tuple


def check(args: Any, sender_moniker: str, message_type: str) -> Tuple[bool, int]:
    """Return ``(allowed, remaining)`` for a sender/message_type pair.

    Reads ``engine.__message_type.rate_limit_per_hour`` and the
    current hour bucket's ``engine.__message_rate_limit.message_count``.
    A zero ``rate_limit_per_hour`` means unlimited.
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT rate_limit_per_hour FROM engine.__message_type
                WHERE type_name = %s
                """,
            (message_type,),
        )
        row = cur.fetchone()

        if not row or row[0] == 0:
            return True, 999

        rate_limit = row[0]
        hour_bucket = datetime.now().replace(minute=0, second=0, microsecond=0)

        cur.execute(
            """
                SELECT message_count FROM engine.__message_rate_limit
                WHERE sender_moniker = %s AND message_type = %s AND hour_bucket = %s
                """,
            (sender_moniker, message_type, hour_bucket),
        )
        row = cur.fetchone()

        current_count = row[0] if row else 0
        remaining = max(0, rate_limit - current_count)

        return current_count < rate_limit, remaining


def record(args: Any, sender_moniker: str, message_type: str) -> None:
    """UPSERT into ``engine.__message_rate_limit`` for the current hour."""
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        hour_bucket = datetime.now().replace(minute=0, second=0, microsecond=0)

        cur.execute(
            """
            INSERT INTO engine.__message_rate_limit (sender_moniker, message_type, hour_bucket, message_count)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (sender_moniker, message_type, hour_bucket)
            DO UPDATE SET message_count = engine.__message_rate_limit.message_count + 1
            """,
            (sender_moniker, message_type, hour_bucket),
        )
        conn.commit()


def get_type_limit(args: Any, message_type: str) -> int:
    """Return the per-hour rate limit for a message type.

    Returns 0 when the type is not registered (interpreted as
    "unlimited" by callers).
    """
    from bbsengine6.message.dal._pool import _connect_ctx

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT rate_limit_per_hour FROM engine.__message_type
                WHERE type_name = %s
                """,
            (message_type,),
        )
        row = cur.fetchone()
        return row[0] if row else 0
