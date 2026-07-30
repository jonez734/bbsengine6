# message.py
# Unified message system with channel-based pub/sub and persistence

from __future__ import annotations

import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from functools import wraps

from psycopg import sql
from psycopg import errors as psycopg_errors

from . import database, io
from .database import getpool

_message_enabled: bool = True
_message_queues = {}
_message_queues_lock = defaultdict(dict)


class MessageUrgency(Enum):
    ROUTINE = "ROUTINE"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


@dataclass
class Message:
    id: int
    channel: str
    sender_moniker: Optional[str]
    content: str
    data: Optional[Dict[str, Any]] = None
    urgency: str = "ROUTINE"
    template: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None
    datestamp: Optional[datetime] = None

    @property
    def timestamp(self) -> float:
        return self.datestamp.timestamp() if self.datestamp else 0.0

    @property
    def recipients(self) -> List[str]:
        return _get_message_recipients(self.id, self.channel)


def is_enabled() -> bool:
    return _message_enabled


def enable() -> None:
    global _message_enabled
    _message_enabled = True


def disable() -> None:
    global _message_enabled
    _message_enabled = False


def _default_db() -> str:
    return os.environ.get("BBSENGINE6_DBNAME", "bbsengine6")


def _resolve_db(database: Optional[str] = None, args: Any = None) -> str:
    if database is not None:
        return database
    if args is not None:
        arg_db = getattr(args, "databasename", None) or getattr(args, "database", None)
        if arg_db:
            return arg_db
    return _default_db()


def _table_identifier(table: str) -> sql.Identifier:
    if "." in table:
        schema, table_name = table.split(".", 1)
        return sql.Identifier(schema, table_name)
    return sql.Identifier(table)


def _make_args(database: str) -> Any:
    """Create args object for database functions."""

    class _Args:
        pass

    args = _Args()
    args.database = database
    args.databasename = database
    return args


def _check_blocking_and_ratelimit(
    sender_moniker: Optional[str],
    channel: str,
    recipient_monikers: Optional[List[str]],
    database: Optional[str],
) -> "tuple[Optional[List[str]], bool, Dict[str, Any]]":
    """Apply rate limiting and blocking checks before insertion.

    Returns:
        (allowed_recipients, rate_limit_ok, diagnostics) where
        ``allowed_recipients`` is None if rate-limited, otherwise the
        filtered list with blocked recipients removed.
        ``diagnostics`` always contains keys ``rate_limit_ok``,
        ``recipients_blocked`` and ``recipients_skipped`` for callers
        that want to surface per-recipient stats.
    """
    diagnostics: Dict[str, Any] = {
        "rate_limit_ok": True,
        "recipients_blocked": [],
        "recipients_skipped": [],
    }

    if sender_moniker is not None:
        allowed, _remaining = check_rate_limit(
            sender_moniker, channel, database=database
        )
        if not allowed:
            diagnostics["rate_limit_ok"] = False
            return None, False, diagnostics

    allowed_recipients: Optional[List[str]] = None
    if recipient_monikers:
        allowed_recipients = []
        for recipient in recipient_monikers:
            if sender_moniker is not None and is_blocked(
                recipient, sender_moniker, database=database
            ):
                diagnostics["recipients_blocked"].append(recipient)
                continue
            allowed_recipients.append(recipient)
        diagnostics["recipients_skipped"] = [
            r for r in recipient_monikers if r not in allowed_recipients
        ]

    return allowed_recipients, True, diagnostics


def store_message(
    channel: str,
    sender_moniker: Optional[str],
    content: str,
    recipient_monikers: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: str = "ROUTINE",
    template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
) -> int:
    """Store a message in the database and create recipients.

    Applies rate limiting (per ``check_rate_limit``) and recipient
    blocking (per ``is_blocked``) before insertion. If the sender is
    over the rate limit, no message is stored and ``0`` is returned.
    Blocked recipients are silently dropped; the message is still
    stored for the rest.

    For richer return data (full result dict with per-recipient
    diagnostics), use :func:`store_message_with_checks`.

    Args:
        channel: Channel name (e.g., 'casino:table:blackjack-1')
        sender_moniker: Sender's moniker (None for system)
        content: Message content
        recipient_monikers: List of recipients (if None, message is broadcast-only)
        data: Optional JSON data
        urgency: Message urgency (ROUTINE, IMPORTANT, URGENT, CRITICAL)
        template: Optional template for rendering
        template_vars: Variables for template rendering
        database: Database name

    Returns:
        Message ID, or 0 if the message system is disabled or the
        sender is rate-limited.
    """
    result = store_message_with_checks(
        channel=channel,
        sender_moniker=sender_moniker,
        content=content,
        recipient_monikers=recipient_monikers,
        data=data,
        urgency=urgency,
        template=template,
        template_vars=template_vars,
        database=database,
    )
    return result.get("message_id", 0)


def store_message_with_checks(
    channel: str,
    sender_moniker: Optional[str],
    content: str,
    recipient_monikers: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: str = "ROUTINE",
    template: Optional[str] = None,
    template_vars: Optional[Dict[str, Any]] = None,
    database: Optional[str] = None,
) -> Dict[str, Any]:
    """Store a message and return full per-recipient diagnostics.

    Applies rate limiting and recipient blocking. Returns a dict
    with::

        {
            "message_id": int,           # 0 if denied or disabled
            "rate_limit_ok": bool,
            "recipients_stored": List[str],
            "recipients_blocked": List[str],
            "recipients_skipped": List[str],
        }

    Use this when callers need to know which recipients were dropped
    and why. :func:`store_message` is a thin wrapper that returns
    only the message id.
    """
    empty: Dict[str, Any] = {
        "message_id": 0,
        "rate_limit_ok": True,
        "recipients_stored": [],
        "recipients_blocked": [],
        "recipients_skipped": [],
    }

    if not _message_enabled:
        return empty

    database = _resolve_db(database)

    if recipient_monikers:
        expanded = resolve_recipients(recipient_monikers, database=database)
        recipient_monikers = expanded

    allowed_recipients, rate_limit_ok, diagnostics = _check_blocking_and_ratelimit(
        sender_moniker, channel, recipient_monikers, database
    )

    if not rate_limit_ok:
        return {
            "message_id": 0,
            "rate_limit_ok": False,
            "recipients_stored": [],
            "recipients_blocked": diagnostics.get("recipients_blocked", []),
            "recipients_skipped": diagnostics.get("recipients_skipped", []),
        }

    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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

            stored: List[str] = []
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
                    stored.append(recipient)

            if sender_moniker is not None:
                record_message_sent(sender_moniker, channel, database=database)

            conn.commit()
            return {
                "message_id": message_id,
                "rate_limit_ok": True,
                "recipients_stored": stored,
                "recipients_blocked": diagnostics.get("recipients_blocked", []),
                "recipients_skipped": diagnostics.get("recipients_skipped", []),
            }


def get_pending_messages(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get pending messages for a user (delivered on connect).

    Args:
        moniker: User's moniker
        limit: Max messages to return
        database: Database name

    Returns:
        List of message dicts with delivery status
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id, m.channel, m.sender_moniker, m.content, m.data,
                    m.urgency, m.template, m.template_vars, m.datestamp,
                    r.status, r.datedelivered, r.dateread
                FROM engine.__message m
                JOIN engine.__message_recipient r ON r.message_id = m.id
                WHERE r.recipient_moniker = %s AND r.status IN ('pending', 'delivered')
                ORDER BY m.datestamp DESC
                LIMIT %s
                """,
                (moniker, limit),
            )
            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append(
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
                )

            return messages


def get_pending_messages_prioritized(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get pending messages for a user, ordered by urgency first.

    CRITICAL and URGENT messages are surfaced before ROUTINE/IMPORTANT
    ones, regardless of datestamp. Within the same urgency bucket,
    messages are ordered most-recent-first.

    Same return shape as :func:`get_pending_messages`.
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id, m.channel, m.sender_moniker, m.content, m.data,
                    m.urgency, m.template, m.template_vars, m.datestamp,
                    r.status, r.datedelivered, r.dateread
                FROM engine.__message m
                JOIN engine.__message_recipient r ON r.message_id = m.id
                WHERE r.recipient_moniker = %s AND r.status IN ('pending', 'delivered')
                ORDER BY
                    CASE m.urgency
                        WHEN 'CRITICAL' THEN 0
                        WHEN 'URGENT'    THEN 1
                        WHEN 'IMPORTANT' THEN 2
                        WHEN 'ROUTINE'   THEN 3
                        ELSE 4
                    END ASC,
                    m.datestamp DESC
                LIMIT %s
                """,
                (moniker, limit),
            )
            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append(
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
                )

            return messages


def mark_delivered(
    message_id: int,
    moniker: str,
    database: Optional[str] = None,
) -> None:
    """Mark a message as delivered.

    Args:
        message_id: Message ID
        moniker: Recipient's moniker
        database: Database name
    """
    if not _message_enabled:
        return

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE engine.__message_recipient 
                SET status = 'delivered', datedelivered = now()
                WHERE message_id = %s AND recipient_moniker = %s
                """,
                (message_id, moniker),
            )
            conn.commit()


def mark_read(
    message_id: int,
    moniker: str,
    database: Optional[str] = None,
) -> None:
    """Mark a message as read.

    Args:
        message_id: Message ID
        moniker: Recipient's moniker
        database: Database name
    """
    if not _message_enabled:
        return

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE engine.__message_recipient 
                SET status = 'read', dateread = now()
                WHERE message_id = %s AND recipient_moniker = %s
                """,
                (message_id, moniker),
            )
            conn.commit()


def get_unread_count(
    moniker: str,
    database: Optional[str] = None,
    *,
    args: Any = None,
    pool: Any = None,
    conn: Any = None,
) -> int:
    """Get count of unread messages for a user.

    Args:
        moniker: User's moniker
        database: Database name (overrides args.databasename)
        args: Optional argparse.Namespace; args.databasename is used
            when no explicit database/pool/conn is supplied.
        pool: Optional pre-existing ConnectionPool to reuse.
        conn: Optional pre-existing connection to use directly.

    Returns:
        Count of unread messages
    """
    if not _message_enabled:
        return 0

    try:
        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM engine.__message_recipient
                    WHERE recipient_moniker = %s AND status = 'pending'
                    """,
                    (moniker,),
                )
                return cur.fetchone()[0]

        if pool is None:
            database = _resolve_db(database, args)
            args = _make_args(database)
            pool = getpool(args)

        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM engine.__message_recipient
                    WHERE recipient_moniker = %s AND status = 'pending'
                    """,
                    (moniker,),
                )
                return cur.fetchone()[0]
    except psycopg_errors.UndefinedTable:
        db_label = database
        if db_label is None and args is not None:
            db_label = getattr(args, "databasename", None)
        io.echo(
            f"bbsengine6.message.get_unread_count.100: "
            f"engine.__message_recipient missing in {db_label or 'current db'}; "
            f"returning 0 (run checkmessage + migrate_notify_to_message.sql "
            f"to install the unified message schema)",
            level="warn",
        )
        return 0


# NOTE: _local_unread_cache is process-local. When a single Python
# process serves multiple BBS sessions (e.g. a multi-user TUI host),
# the count is shared across all monikers in that process. In a
# typical BED/TUI deployment there is one TUI process per user, so
# this is fine. Callers that need authoritative counts should fall
# back to get_unread_count() which queries the database.
_local_unread_cache: Dict[str, int] = {}
_local_unread_cache_lock: Optional[Any] = None


def _ensure_local_lock() -> Any:
    """Lazily import threading.Lock (only when cache is used)."""
    global _local_unread_cache_lock
    if _local_unread_cache_lock is None:
        import threading

        _local_unread_cache_lock = threading.Lock()
    return _local_unread_cache_lock


def get_local_unread_count(moniker: str) -> int:
    """Return the locally cached unread count for a moniker.

    The cache is updated by `set_local_unread_count()` and
    `bump_local_unread_count()`, typically called by the message-client
    when a server-push notification arrives. Returns -1 if not cached
    (caller should fall back to `get_unread_count()` for an authoritative
    DB-backed value).
    """
    lock = _ensure_local_lock()
    with lock:
        return _local_unread_cache.get(moniker, -1)


def set_local_unread_count(moniker: str, count: int) -> None:
    """Set the local cache to a specific count."""
    lock = _ensure_local_lock()
    with lock:
        _local_unread_cache[moniker] = max(0, int(count))


def bump_local_unread_count(moniker: str, delta: int = 1) -> None:
    """Atomically adjust the local cache by `delta`."""
    lock = _ensure_local_lock()
    with lock:
        current = _local_unread_cache.get(moniker, 0)
        _local_unread_cache[moniker] = max(0, current + int(delta))


def clear_local_unread_cache() -> None:
    """Clear the entire local cache (e.g. on logout)."""
    lock = _ensure_local_lock()
    with lock:
        _local_unread_cache.clear()


def deliver_pending_on_connect(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Deliver all pending messages to user on connect.

    Uses :func:`get_pending_messages_prioritized` so that
    CRITICAL/URGENT messages are surfaced first, regardless of
    datestamp.

    Args:
        moniker: User's moniker
        database: Database name

    Returns:
        List of pending messages
    """
    if not _message_enabled:
        return []

    messages = get_pending_messages_prioritized(moniker, database=database)

    for msg in messages:
        mark_delivered(msg["id"], moniker, database=database)

    return messages


# =============================================================================
# Phase 1C: Groups, Blocking, Rate Limiting
# =============================================================================


def create_message_group(
    name: str,
    createdby: Optional[str] = None,
    description: Optional[str] = None,
    database: Optional[str] = None,
) -> int:
    """Create a message group (distribution list).

    Args:
        name: Group name
        createdby: Creator's moniker
        description: Optional description
        database: Database name

    Returns:
        Group ID
    """
    if not _message_enabled:
        return 0

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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


def add_to_message_group(
    group_id: int,
    member_moniker: str,
    addedby: Optional[str] = None,
    database: Optional[str] = None,
) -> bool:
    """Add a member to a message group.

    Args:
        group_id: Group ID
        member_moniker: Member to add
        addedby: Who added them
        database: Database name

    Returns:
        True if added successfully
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__message_group_member (group_id, member_moniker, addedby)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (group_id, member_moniker, addedby),
            )
            conn.commit()
            return True


def get_message_group_members(
    group_id: int,
    database: Optional[str] = None,
) -> List[str]:
    """Get all members of a message group.

    Args:
        group_id: Group ID
        database: Database name

    Returns:
        List of member monikers
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT member_moniker FROM engine.__message_group_member
                WHERE group_id = %s
                """,
                (group_id,),
            )
            return [row[0] for row in cur.fetchall()]


def get_user_groups(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get all groups a user belongs to.

    Args:
        moniker: User's moniker
        database: Database name

    Returns:
        List of group dicts
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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


def block_sender(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Block a sender from messaging the blocker.

    Args:
        blocker_moniker: Who is blocking
        blocked_moniker: Who is being blocked
        database: Database name

    Returns:
        True if blocked successfully
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__message_block (blocker_moniker, blocked_moniker)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING
                """,
                (blocker_moniker, blocked_moniker),
            )
            conn.commit()
            return True


def unblock_sender(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Unblock a sender.

    Args:
        blocker_moniker: Who is unblocking
        blocked_moniker: Who is being unblocked
        database: Database name

    Returns:
        True if unblocked successfully
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM engine.__message_block
                WHERE blocker_moniker = %s AND blocked_moniker = %s
                """,
                (blocker_moniker, blocked_moniker),
            )
            conn.commit()
            return True


def is_blocked(
    blocker_moniker: str,
    blocked_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Check if a sender is blocked by a recipient.

    Args:
        blocker_moniker: Who would be receiving
        blocked_moniker: Who would be sending

    Returns:
        True if blocked
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM engine.__message_block
                WHERE blocker_moniker = %s AND blocked_moniker = %s
                """,
                (blocker_moniker, blocked_moniker),
            )
            return cur.fetchone() is not None


def check_rate_limit(
    sender_moniker: str,
    message_type: str,
    database: Optional[str] = None,
) -> tuple[bool, int]:
    """Check if sender has exceeded rate limit for a message type.

    Args:
        sender_moniker: Sender's moniker
        message_type: Message type (e.g., 'system:shout', 'member:direct')
        database: Database name

    Returns:
        Tuple of (allowed, remaining_count)
    """
    if not _message_enabled:
        return True, 999

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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


def record_message_sent(
    sender_moniker: str,
    message_type: str,
    database: Optional[str] = None,
) -> bool:
    """Record a message sent for rate limiting.

    Args:
        sender_moniker: Sender's moniker
        message_type: Message type
        database: Database name

    Returns:
        True if recorded
    """
    if not _message_enabled:
        return True

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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
            return True


def get_message_type_rate_limit(
    message_type: str,
    database: Optional[str] = None,
) -> int:
    """Get rate limit for a message type.

    Args:
        message_type: Message type name
        database: Database name

    Returns:
        Rate limit per hour (0 = unlimited)
    """
    if not _message_enabled:
        return 0

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT rate_limit_per_hour FROM engine.__message_type
                WHERE type_name = %s
                """,
                (message_type,),
            )
            row = cur.fetchone()
            return row[0] if row else 0


# =============================================================================
# Phase 1E: Templating
# =============================================================================

import re


def render_template(
    template: str,
    variables: Dict[str, Any],
) -> str:
    """Render a template with variable substitution.

    Variables are in the format {variable_name} or ${variable_name}.

    Args:
        template: Template string with {variable} placeholders
        variables: Dict of variable names to values

    Returns:
        Rendered string with variables replaced
    """
    if not template:
        return ""

    result = template

    for var_name, var_value in variables.items():
        if var_value is None:
            var_value = ""

        result = result.replace("{" + var_name + "}", str(var_value))
        result = result.replace("$" + var_name, str(var_value))

    return result


def render_message_content(
    content: str,
    template: Optional[str],
    template_vars: Optional[Dict[str, Any]],
) -> str:
    """Render message content with optional template.

    If template is provided, render it with template_vars.
    Otherwise, return content as-is.

    Args:
        content: Default content if no template
        template: Template string
        template_vars: Variables for template

    Returns:
        Rendered content
    """
    if template and template_vars:
        return render_template(template, template_vars)

    if template:
        return template

    return content


def parse_variables_from_content(content: str) -> List[str]:
    """Extract variable names from content.

    Finds all {variable} and $variable patterns.

    Args:
        content: Content to parse

    Returns:
        List of variable names found
    """
    curly_vars = re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", content)
    dollar_vars = re.findall(r"\$([a-zA-Z_][a-zA-Z0-9_]*)", content)

    variables = list(set(curly_vars + dollar_vars))
    return sorted(variables)


def get_builtin_variables() -> Dict[str, Any]:
    """Get built-in variables available for all messages.

    Returns:
        Dict of builtin variable names to placeholder functions
    """
    from datetime import datetime

    return {
        "year": datetime.now().year,
        "month": datetime.now().month,
        "day": datetime.now().day,
        "hour": datetime.now().hour,
        "minute": datetime.now().minute,
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
    }


def validate_template(template: str) -> tuple[bool, List[str]]:
    """Validate a template string.

    Args:
        template: Template string

    Returns:
        Tuple of (is_valid, list of errors)
    """
    errors = []

    if not template:
        return True, []

    open_curly = template.count("{")
    close_curly = template.count("}")
    if open_curly != close_curly:
        errors.append(f"Unmatched curly braces: {open_curly} open, {close_curly} close")

    dollar_open = len(re.findall(r"\$[a-zA-Z_]", template))
    dollar_close = template.count("}")
    if dollar_open != 0 and dollar_open != dollar_close:
        errors.append(
            f"Unmatched $ variables: {dollar_open} open, {dollar_close} close"
        )

    invalid_vars = re.findall(r"\{[^a-zA-Z_]", template)
    if invalid_vars:
        errors.append(f"Invalid variable syntax: {invalid_vars}")

    return len(errors) == 0, errors


# =============================================================================
# Phase 1 gap-fills (ported from notify/message_delivery)
# =============================================================================


def remove_from_group(
    group_id: int,
    member_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Remove a member from a message group.

    Args:
        group_id: Group ID
        member_moniker: Member to remove
        database: Database name

    Returns:
        True if a row was removed, False otherwise
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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


def get_blocked(
    moniker: str,
    database: Optional[str] = None,
) -> List[str]:
    """List the monikers that have blocked ``moniker`` (i.e. senders
    whose messages are silently dropped by recipients blocking them).

    Semantically this is the inverse of ``is_blocked``: for each row
    in ``engine.__message_block`` where ``blocked_moniker = moniker``,
    return the corresponding ``blocker_moniker``. This matches the
    notify-era ``get_blocked(moniker)`` which returned "who has
    blocked me".

    Args:
        moniker: Sender whose block-list is requested
        database: Database name

    Returns:
        List of blocker monikers (may be empty)
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT blocker_moniker FROM engine.__message_block
                WHERE blocked_moniker = %s
                """,
                (moniker,),
            )
            return [row[0] for row in cur.fetchall()]


def get_urgent(
    moniker: str,
    limit: int = 50,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get URGENT/CRITICAL unread messages for a user.

    Equivalent to ``get_pending_messages_prioritized`` with a
    pre-filter on urgency, plus a tighter limit. Returned messages
    are in urgency-then-datestamp order.

    Args:
        moniker: Recipient's moniker
        limit: Max messages to return
        database: Database name

    Returns:
        List of message dicts (same shape as
        ``get_pending_messages``)
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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
                (moniker, limit),
            )
            rows = cur.fetchall()

            messages = []
            for row in rows:
                messages.append(
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
                )
            return messages


def expunge(
    message_id: int,
    sender_moniker: str,
    database: Optional[str] = None,
) -> bool:
    """Sender-side hard delete of a message.

    Deletes the row from ``engine.__message`` (cascading to
    ``engine.__message_recipient``) only if ``sender_moniker``
    matches. Returns True on success, False if the message does
    not exist, was already deleted, or belongs to a different
    sender.

    Args:
        message_id: Message ID
        sender_moniker: Sender's moniker (authorization check)
        database: Database name

    Returns:
        True if a row was deleted, False otherwise
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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


def get_queue(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return pending messages for ``moniker``.

    Notify-era API. Equivalent to
    ``get_pending_messages(moniker, limit=1000)`` with a generous
    default limit; returns DB-backed results (the notify
    implementation returned an in-memory queue).

    Args:
        moniker: Recipient's moniker
        database: Database name

    Returns:
        List of pending message dicts
    """
    return get_pending_messages(moniker, limit=1000, database=database)


def resolve_recipients(
    recipients: List[str],
    database: Optional[str] = None,
) -> List[str]:
    """Expand ``@group_name`` and ``@everyone`` references.

    Notify auto-expanded these in ``send()``. Returns a flat list
    of monikers:

    - ``@everyone`` expands to every approved member
    - ``@group_name`` expands to the members of the named
      ``engine.__message_group`` (using
      ``get_message_group_members``)

    Expansion is recursive for nested groups, with a depth cap
    to prevent infinite loops.

    Args:
        recipients: List of recipients (plain monikers, ``@group``,
            or ``@everyone``)
        database: Database name

    Returns:
        Flat list of monikers, with duplicates removed (order
        preserved by first occurrence).
    """
    if not _message_enabled:
        return []

    seen: Set[str] = set()
    expanded: List[str] = []

    def _add(moniker: str) -> None:
        if moniker and moniker not in seen:
            seen.add(moniker)
            expanded.append(moniker)

    pending = list(recipients)
    depth = 0
    MAX_DEPTH = 10

    while pending and depth < MAX_DEPTH:
        depth += 1
        next_pending: List[str] = []
        for r in pending:
            if not r:
                continue
            if r.startswith("@"):
                token = r[1:].strip()
                if not token:
                    continue
                if token.lower() == "everyone":
                    database_name = _resolve_db(database)
                    args = _make_args(database_name)
                    pool = getpool(args)
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT moniker FROM engine.__member "
                                "WHERE approved = TRUE"
                            )
                            for row in cur.fetchall():
                                _add(row[0])
                else:
                    database_name = _resolve_db(database)
                    args = _make_args(database_name)
                    pool = getpool(args)
                    with pool.connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "SELECT id FROM engine.__message_group "
                                "WHERE name = %s",
                                (token,),
                            )
                            row = cur.fetchone()
                            if row:
                                group_id = row[0]
                                members = get_message_group_members(
                                    group_id, database=database_name
                                )
                                for m in members:
                                    _add(m)
            else:
                _add(r)
        if not next_pending:
            break
        pending = next_pending

    return expanded


def set_rate_limit(
    type_name: str,
    limit: int,
    database: Optional[str] = None,
) -> bool:
    """Runtime adjustment of the per-hour rate limit for a
    message type.

    Creates the type row if it does not already exist (with the
    new limit and an empty description).

    Args:
        type_name: Message type name (channel)
        limit: New per-hour limit (0 = unlimited)
        database: Database name

    Returns:
        True on success
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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
            return True


def register_type(
    type_name: str,
    description: str = "",
    rate_limit_per_hour: int = 0,
    requires_approval: bool = False,
    database: Optional[str] = None,
) -> bool:
    """Register a new message type at runtime.

    Idempotent: updates the existing row if ``type_name`` is
    already registered, otherwise inserts a new row.

    Args:
        type_name: Unique type name (e.g. ``"casino:table"``)
        description: Human-readable description
        rate_limit_per_hour: Per-hour send limit (0 = unlimited)
        requires_approval: Whether posts need moderator approval
        database: Database name

    Returns:
        True on success
    """
    if not _message_enabled:
        return False

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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
            return True


def get_types(
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return all registered message types.

    Args:
        database: Database name

    Returns:
        List of type dicts with keys ``type_name``,
        ``description``, ``rate_limit_per_hour``,
        ``requires_approval``, ``datemodified``.
    """
    if not _message_enabled:
        return []

    database = _resolve_db(database)
    args = _make_args(database)
    pool = getpool(args)

    with pool.connection() as conn:
        with conn.cursor() as cur:
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
