# bbsengine6/message/dal/messages.py
#
# DAL functions for engine.__message and engine.__message_recipient.
# Pure Postgres I/O. Service-layer wrappers live in
# ``bbsengine6.message.service`` and add the enable/disable gate,
# rate-limit gating, and recipient expansion.

from __future__ import annotations

from typing import Any, Dict, List, Optional

from bbsengine6.message.dal._pool import _connect_ctx, table_exists


def store_message_with_recipients(
    args: Any,
    channel: str,
    sender_moniker: Optional[str],
    content: str,
    data: Optional[Dict[str, Any]],
    urgency: str,
    template: Optional[str],
    template_vars: Optional[Dict[str, Any]],
    allowed_recipients: Optional[List[str]],
) -> int:
    """INSERT a row into ``engine.__message`` and one row per
    allowed recipient into ``engine.__message_recipient``.

    Returns the new ``message_id``. No rate-limit, blocking, or
    enable/disable checks are performed here -- that is the service
    layer's job. ``allowed_recipients`` may be ``None`` for a
    broadcast-only message.
    """
    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO engine.__message
            (channel, sender_moniker, content, data, urgency, template, template_vars)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                channel,
                sender_moniker,
                content,
                data,
                urgency,
                template,
                template_vars,
            ),
        )
        message_id = cur.fetchone()[0]

        if allowed_recipients:
            for recipient in allowed_recipients:
                cur.execute(
                    """
                    INSERT INTO engine.__message_recipient (message_id, recipient_moniker)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (message_id, recipient),
                )

        conn.commit()
        return message_id


def list_pending_for_recipient(
    args: Any,
    recipient_moniker: str,
    limit: int,
    *,
    prioritized: bool = False,
) -> List[Dict[str, Any]]:
    """SELECT pending+delivered messages for a recipient.

    When ``prioritized`` is True, CRITICAL/URGENT messages are
    surfaced before ROUTINE/IMPORTANT ones (urgency-then-datestamp
    ordering). When False, plain datestamp-DESC ordering is used.
    Returned dicts have the keys: ``id, channel, sender_moniker,
    content, data, urgency, template, template_vars, datestamp,
    status, datedelivered, dateread``.
    """
    order_clause = (
        """
                ORDER BY
                    CASE m.urgency
                        WHEN 'CRITICAL' THEN 0
                        WHEN 'URGENT'    THEN 1
                        WHEN 'IMPORTANT' THEN 2
                        WHEN 'ROUTINE'   THEN 3
                        ELSE 4
                    END ASC,
                    m.datestamp DESC
        """
        if prioritized
        else "ORDER BY m.datestamp DESC"
    )

    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            f"""
                SELECT
                    m.id, m.channel, m.sender_moniker, m.content, m.data,
                    m.urgency, m.template, m.template_vars, m.datestamp,
                    r.status, r.datedelivered, r.dateread
                FROM engine.__message m
                JOIN engine.__message_recipient r ON r.message_id = m.id
                WHERE r.recipient_moniker = %s AND r.status IN ('pending', 'delivered')
                {order_clause}
                LIMIT %s
                """,
            (recipient_moniker, limit),
        )
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "channel": row[1],
            "sender_moniker": row[2],
            "content": row[3],
            "data": row[4],
            "urgency": row[5],
            "template": row[6],
            "template_vars": row[7],
            "datestamp": row[8],
            "status": row[9],
            "datedelivered": row[10],
            "dateread": row[11],
        }
        for row in rows
    ]


def list_urgent_for_recipient(
    args: Any,
    recipient_moniker: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """SELECT URGENT/CRITICAL pending+delivered messages."""
    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT
                    m.id, m.channel, m.sender_moniker, m.content, m.data,
                    m.urgency, m.template, m.template_vars, m.datestamp,
                    r.status, r.datedelivered, r.dateread
                FROM engine.__message m
                JOIN engine.__message_recipient r ON r.message_id = m.id
                WHERE r.recipient_moniker = %s
                  AND r.status IN ('pending', 'delivered')
                  AND m.urgency IN ('URGENT', 'CRITICAL')
                ORDER BY
                    CASE m.urgency
                        WHEN 'CRITICAL' THEN 0
                        WHEN 'URGENT'    THEN 1
                        ELSE 2
                    END ASC,
                    m.datestamp DESC
                LIMIT %s
                """,
            (recipient_moniker, limit),
        )
        rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "channel": row[1],
            "sender_moniker": row[2],
            "content": row[3],
            "data": row[4],
            "urgency": row[5],
            "template": row[6],
            "template_vars": row[7],
            "datestamp": row[8],
            "status": row[9],
            "datedelivered": row[10],
            "dateread": row[11],
        }
        for row in rows
    ]


def mark_delivered(args: Any, message_id: int, recipient_moniker: str) -> None:
    """UPDATE ``engine.__message_recipient`` to ``delivered``."""
    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                UPDATE engine.__message_recipient
                SET status = 'delivered', datedelivered = now()
                WHERE message_id = %s AND recipient_moniker = %s
                """,
            (message_id, recipient_moniker),
        )
        conn.commit()


def mark_read(args: Any, message_id: int, recipient_moniker: str) -> None:
    """UPDATE ``engine.__message_recipient`` to ``read``."""
    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                UPDATE engine.__message_recipient
                SET status = 'read', dateread = now()
                WHERE message_id = %s AND recipient_moniker = %s
                """,
            (message_id, recipient_moniker),
        )
        conn.commit()


def count_unread_for_recipient(
    args: Any,
    recipient_moniker: str,
    *,
    conn: Any = None,
) -> int:
    """SELECT COUNT(*) of pending rows for a recipient.

    If ``conn`` is supplied, the probe + count run on the caller's
    cursor. Otherwise a fresh connection is opened. Returns 0 if
    ``engine.__message_recipient`` does not exist in the target DB.
    """
    def _work(c: Any) -> int:
        with c.cursor() as cur:
            if not table_exists(cur, "engine", "__message_recipient"):
                return 0
            cur.execute(
                """
                SELECT COUNT(*) FROM engine.__message_recipient
                WHERE recipient_moniker = %s AND status = 'pending'
                """,
                (recipient_moniker,),
            )
            return cur.fetchone()[0]

    if conn is not None:
        return _work(conn)

    with _connect_ctx(args, pool=None) as conn:
        return _work(conn)


def list_recipients(args: Any, message_id: int) -> List[str]:
    """SELECT ``recipient_moniker`` rows for a stored message.

    Used by ``Message.recipients`` (in ``lib.py``). Returns [] when
    the DB pool is unavailable or no rows exist; never raises.
    """
    from bbsengine6 import database

    try:
        pool = database.getpool(None)
    except Exception:
        return []
    if pool is None:
        return []
    try:
        with pool.connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT recipient_moniker FROM engine.__message_recipient "
                "WHERE message_id = %s ORDER BY recipient_moniker",
                (message_id,),
            )
            rows = cur.fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def expunge_sender_message(
    args: Any, message_id: int, sender_moniker: str
) -> bool:
    """DELETE a row from ``engine.__message`` if the sender matches.

    The FK from ``engine.__message_recipient.message_id`` is
    ``on delete cascade`` so recipient rows are removed too.
    Returns True if a row was deleted, False otherwise.
    """
    with _connect_ctx(args, pool=None) as conn, conn.cursor() as cur:
        cur.execute(
            """
                DELETE FROM engine.__message
                WHERE id = %s AND sender_moniker = %s
                """,
            (message_id, sender_moniker),
        )
        removed = cur.rowcount > 0
        conn.commit()
        return removed
