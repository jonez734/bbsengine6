# notify.py
# User notification system with templating, rate limiting, and blocking support.

from __future__ import annotations

import logging
import queue
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import psycopg
from psycopg import sql

from . import database, io

logger = logging.getLogger(__name__)

# Thread-local storage for per-user notification queues
_queues_lock = threading.Lock()
_queues: Dict[str, UserNotificationQueue] = {}
_types_lock = threading.Lock()
_types: Dict[str, Dict[str, Any]] = {}
_rate_limit_lock = threading.Lock()


class NotificationUrgency(Enum):
    """Notification urgency levels."""

    ROUTINE = "ROUTINE"
    IMPORTANT = "IMPORTANT"
    URGENT = "URGENT"
    CRITICAL = "CRITICAL"


@dataclass
class Notification:
    """Represents a single notification with tracking information."""

    id: int
    notification_type: str
    recipients: List[str]
    recipients_ok: List[str]
    recipients_failed: List[str]
    sender_moniker: Optional[str]
    template: str
    template_vars: Dict[str, Any]
    message: str
    data: Dict[str, Any]
    urgency: NotificationUrgency
    timestamp: float
    read_by: Dict[str, float] = field(default_factory=dict)
    delivered_to: Dict[str, float] = field(default_factory=dict)
    blocked_from: Set[str] = field(default_factory=set)
    errors: Dict[str, str] = field(default_factory=dict)
    should_persist: bool = True
    created_at: datetime = field(default_factory=datetime.now)


class UserNotificationQueue:
    """Thread-safe queue for active user session notifications."""

    def __init__(self):
        self._queue: queue.Queue[Notification] = queue.Queue()

    def put(self, notification: Notification) -> None:
        """Add notification to queue."""
        self._queue.put(notification)

    def get(self, timeout: Optional[float] = None) -> Optional[Notification]:
        """Get next notification from queue, blocking with optional timeout."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_all(self) -> List[Notification]:
        """Get all queued notifications without blocking."""
        notifications = []
        try:
            while True:
                notifications.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return notifications

    def peek_urgent(self) -> Optional[Notification]:
        """Peek at urgent notifications without removing them."""
        notifications = self.get_all()
        for n in notifications:
            if n.urgency in (NotificationUrgency.URGENT, NotificationUrgency.CRITICAL):
                self._queue.put(n)
                return n
            # Put it back
            self._queue.put(n)
        return None

    def has_urgent(self) -> bool:
        """Check if queue contains urgent notifications."""
        return self.peek_urgent() is not None

    def size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


def _validate_moniker(moniker: str, cur: Optional[Any] = None) -> bool:
    """Validate that a moniker exists in the database."""
    if not moniker or not isinstance(moniker, str):
        return False
    if len(moniker) > 255:
        return False
    if not re.match(r"^[a-zA-Z0-9_-]+$", moniker):
        return False

    # If no cursor provided, we assume valid (for testing)
    if not cur:
        return True

    # Query database to verify existence
    try:
        cur.execute(
            sql.SQL("SELECT 1 FROM engine.__member WHERE moniker = %s"), (moniker,)
        )
        return cur.fetchone() is not None
    except Exception as e:
        logger.error(f"Error validating moniker {moniker}: {e}")
        return False


def _validate_type_name(type_name: str) -> bool:
    """Validate notification type name format."""
    if not type_name or not isinstance(type_name, str):
        return False
    if len(type_name) > 50:
        return False
    if not re.match(r"^[a-zA-Z0-9_]+$", type_name):
        return False
    return True


def _validate_template(
    template: str, template_vars: Optional[Dict[str, Any]] = None
) -> None:
    """Validate template syntax and variable usage."""
    if not template or not isinstance(template, str):
        raise ValueError("Template must be non-empty string")
    if len(template) > 500:
        raise ValueError("Template exceeds 500 character limit")

    # Find all variable placeholders
    variables = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template))

    # Check for invalid syntax
    invalid = re.findall(r"\{[^}]*[^a-zA-Z0-9_{}][^}]*\}", template)
    if invalid:
        raise ValueError(f"Template contains invalid syntax: {invalid}")

    # Check if all variables are defined
    if template_vars:
        for var in variables:
            if var not in template_vars:
                raise ValueError(
                    f"Template variable '{var}' not defined in template_vars"
                )


def _validate_template_vars(template_vars: Optional[Dict[str, Any]]) -> None:
    """Validate template variables dictionary."""
    if template_vars is None:
        return

    if not isinstance(template_vars, dict):
        raise ValueError("template_vars must be a dictionary")

    total_size = 0
    for key, value in template_vars.items():
        # Validate key
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
            raise ValueError(f"Invalid template variable name: {key}")

        # Validate value type and size
        # Note: bool is a subclass of int, so check bool explicitly first
        if isinstance(value, bool):
            raise ValueError(
                f"Template variable '{key}' must be string, int, or float (not bool)"
            )
        elif isinstance(value, str):
            if len(value) > 100:
                raise ValueError(
                    f"String value for '{key}' exceeds 100 character limit"
                )
            total_size += len(value)
        elif not isinstance(value, (int, float)):
            raise ValueError(f"Template variable '{key}' must be string, int, or float")
        total_size += len(str(value))

    if total_size > 10240:  # 10KB
        raise ValueError("template_vars total size exceeds 10KB limit")


def _render_template(template: str, template_vars: Optional[Dict[str, Any]]) -> str:
    """Render template with variables using safe string formatting."""
    if not template_vars:
        template_vars = {}

    result = template
    for key, value in template_vars.items():
        result = result.replace(f"{{{key}}}", str(value))

    return result


def _expand_recipients(
    recipients: List[str], cur: Any
) -> tuple[List[str], Dict[str, str]]:
    """Expand recipient list, handling groups and @everyone."""
    expanded = []
    errors = {}

    for recipient in recipients:
        if recipient.startswith("@"):
            # Handle special @everyone
            if recipient == "@everyone":
                # Try explicit @everyone group first
                cur.execute(
                    sql.SQL(
                        "SELECT DISTINCT member_moniker FROM engine.__notify_group WHERE group_name = %s"
                    ),
                    ("@everyone",),
                )
                members = [row[0] for row in cur.fetchall()]

                if members:
                    expanded.extend(members)
                else:
                    # Fall back to active sessions
                    cur.execute(
                        sql.SQL("SELECT DISTINCT moniker FROM engine.__session")
                    )
                    active = [row[0] for row in cur.fetchall()]
                    expanded.extend(active)
            else:
                # Regular group
                cur.execute(
                    sql.SQL(
                        "SELECT DISTINCT member_moniker FROM engine.__notify_group WHERE group_name = %s"
                    ),
                    (recipient,),
                )
                members = [row[0] for row in cur.fetchall()]

                if not members:
                    errors[recipient] = "Group does not exist"
                else:
                    expanded.extend(members)
        else:
            # Direct moniker
            if _validate_moniker(recipient, cur):
                expanded.append(recipient)
            else:
                errors[recipient] = (
                    f"Invalid moniker or moniker does not exist: {recipient}"
                )

    return expanded, errors


def _check_is_blocked(
    sender_moniker: Optional[str], recipient_moniker: str, cur: Any
) -> bool:
    """Check if sender's notifications to recipient are blocked."""
    if not sender_moniker:
        return False

    try:
        cur.execute(
            sql.SQL(
                "SELECT 1 FROM engine.__notify_block WHERE blocker_moniker = %s AND sender_moniker = %s"
            ),
            (recipient_moniker, sender_moniker),
        )
        return cur.fetchone() is not None
    except Exception:
        io.echo_traceback("bbsengine6.notify._check_is_blocked.100:")
        return False


def _check_rate_limit(sender_moniker: str, notification_type: str, cur: Any) -> bool:
    """Check if sender has exceeded rate limit for this notification type."""
    try:
        # Get type's max_per_hour
        cur.execute(
            sql.SQL(
                "SELECT max_per_user_per_hour FROM engine.__notify_type WHERE type_name = %s"
            ),
            (notification_type,),
        )
        row = cur.fetchone()
        if not row:
            return True  # Type not registered, allow

        max_per_hour = row[0]

        # Check current window
        cur.execute(
            sql.SQL("""
                SELECT send_count FROM engine.__notify_rate_limit
                WHERE sender_moniker = %s AND notification_type = %s
                AND window_start > now() - interval '1 hour'
            """),
            (sender_moniker, notification_type),
        )
        row = cur.fetchone()
        if row and row[0] >= max_per_hour:
            return False  # Rate limit exceeded

        return True  # Within limit
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True


def _update_rate_limit(sender_moniker: str, notification_type: str, cur: Any) -> None:
    """Update rate limit tracking for sender."""
    try:
        cur.execute(
            sql.SQL("""
                INSERT INTO engine.__notify_rate_limit
                (sender_moniker, notification_type, send_count, window_start, last_updated)
                VALUES (%s, %s, 1, now(), now())
                ON CONFLICT (sender_moniker, notification_type)
                DO UPDATE SET
                    send_count = CASE
                        WHEN (now() - window_start) < interval '1 hour'
                        THEN send_count + 1
                        ELSE 1
                    END,
                    window_start = CASE
                        WHEN (now() - window_start) < interval '1 hour'
                        THEN window_start
                        ELSE now()
                    END,
                    last_updated = now()
            """),
            (sender_moniker, notification_type),
        )
    except Exception as e:
        logger.error(f"Error updating rate limit: {e}")


def send(
    notification_type: str,
    recipients: List[str],
    template: str,
    template_vars: Optional[Dict[str, Any]] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: Optional[NotificationUrgency] = None,
    should_persist: bool = True,
    conn: Optional[Any] = None,
) -> Notification:
    """Send notification to recipients with templating and rate limiting."""

    # Validation
    if not _validate_type_name(notification_type):
        raise ValueError(f"Invalid notification type: {notification_type}")

    _validate_template(template, template_vars)
    _validate_template_vars(template_vars)

    if sender_moniker and not _validate_moniker(sender_moniker):
        raise ValueError(f"Invalid sender moniker: {sender_moniker}")

    if not recipients or not isinstance(recipients, list):
        raise ValueError("recipients must be a non-empty list")

    if template_vars is None:
        template_vars = {}
    if data is None:
        data = {}

    # Render message
    message = _render_template(template, template_vars)

    # Use provided connection or create new one
    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            # Auto-register type if needed
            cur.execute(
                sql.SQL(
                    "SELECT default_urgency FROM engine.__notify_type WHERE type_name = %s"
                ),
                (notification_type,),
            )
            type_row = cur.fetchone()

            if not type_row:
                # Auto-register with defaults
                default_urg = NotificationUrgency.ROUTINE.value
                cur.execute(
                    sql.SQL("""
                        INSERT INTO engine.__notify_type
                        (type_name, default_urgency, max_per_user_per_hour, persist_by_default, registered_at)
                        VALUES (%s, %s, 10, true, now())
                    """),
                    (notification_type, default_urg),
                )
                type_urgency = default_urg
            else:
                type_urgency = type_row[0]

            # Determine urgency
            if urgency is None:
                urgency = NotificationUrgency(type_urgency)

            # Check rate limit
            if sender_moniker and not _check_rate_limit(
                sender_moniker, notification_type, cur
            ):
                raise RuntimeError(f"Rate limit exceeded for {notification_type}")

            # Expand recipients
            expanded, errors = _expand_recipients(recipients, cur)

            # Insert core notification
            cur.execute(
                sql.SQL("""
                    INSERT INTO engine.__notify
                    (notification_type, sender_moniker, template, template_vars, rendered_message, data, urgency, should_persist, datecreated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    RETURNING id
                """),
                (
                    notification_type,
                    sender_moniker,
                    template,
                    template_vars,
                    message,
                    data,
                    urgency.value,
                    should_persist,
                ),
            )
            notify_id = cur.fetchone()[0]

            # Insert per-recipient tracking
            recipients_ok = []
            for recipient in expanded:
                is_blocked = _check_is_blocked(sender_moniker, recipient, cur)

                cur.execute(
                    sql.SQL("""
                        INSERT INTO engine.__notify_recipient
                        (notify_id, recipient_moniker, is_blocked, datecreated)
                        VALUES (%s, %s, %s, now())
                    """),
                    (notify_id, recipient, is_blocked),
                )

                if not is_blocked:
                    recipients_ok.append(recipient)
                    # Add to live queue if user has one
                    _add_to_user_queue(
                        recipient,
                        notify_id,
                        message,
                        urgency,
                        template_vars,
                        data,
                        notification_type,
                        sender_moniker,
                        template,
                    )

            # Update rate limit
            if sender_moniker:
                _update_rate_limit(sender_moniker, notification_type, cur)

            conn.commit()

        return Notification(
            id=notify_id,
            notification_type=notification_type,
            recipients=recipients,
            recipients_ok=recipients_ok,
            recipients_failed=[r for r in expanded if r not in recipients_ok],
            sender_moniker=sender_moniker,
            template=template,
            template_vars=template_vars,
            message=message,
            data=data,
            urgency=urgency,
            timestamp=time.time(),
            errors=errors,
            should_persist=should_persist,
            created_at=datetime.now(),
        )
    finally:
        if should_close_conn:
            conn.close()


def _add_to_user_queue(
    moniker: str,
    notify_id: int,
    message: str,
    urgency: NotificationUrgency,
    template_vars: Dict,
    data: Dict,
    notification_type: str,
    sender_moniker: Optional[str],
    template: str,
) -> None:
    """Add notification to user's live queue if they have one."""
    with _queues_lock:
        if moniker in _queues:
            notification = Notification(
                id=notify_id,
                notification_type=notification_type,
                recipients=[moniker],
                recipients_ok=[moniker],
                recipients_failed=[],
                sender_moniker=sender_moniker,
                template=template,
                template_vars=template_vars,
                message=message,
                data=data,
                urgency=urgency,
                timestamp=time.time(),
                should_persist=True,
                created_at=datetime.now(),
            )
            _queues[moniker].put(notification)

            # Mark as delivered
            try:
                conn = psycopg.connect("dbname=postgres")
                with database.cursor(conn) as cur:
                    cur.execute(
                        sql.SQL(
                            "UPDATE engine.__notify_recipient SET delivered_at = now() WHERE notify_id = %s AND recipient_moniker = %s"
                        ),
                        (notify_id, moniker),
                    )
                    conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"Could not mark delivered: {e}")


def get_notifications(
    moniker: str,
    unread_only: bool = False,
    limit: int = 100,
    conn: Optional[Any] = None,
) -> List[Notification]:
    """Retrieve notifications for a user from database."""
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            if unread_only:
                query = sql.SQL("""
                    SELECT n.id, n.notification_type, n.sender_moniker, n.template, n.template_vars,
                           n.rendered_message, n.data, n.urgency, n.datecreated, nr.read_at, nr.delivered_at
                    FROM engine.notify_unread
                    WHERE recipient_moniker = %s
                    ORDER BY datecreated DESC
                    LIMIT %s
                """)
            else:
                query = sql.SQL("""
                    SELECT n.id, n.notification_type, n.sender_moniker, n.template, n.template_vars,
                           n.rendered_message, n.data, n.urgency, n.datecreated, nr.read_at, nr.delivered_at
                    FROM engine.notify
                    WHERE recipient_moniker = %s
                    ORDER BY datecreated DESC
                    LIMIT %s
                """)

            cur.execute(query, (moniker, limit))
            rows = cur.fetchall()

            notifications = []
            for row in rows:
                notifications.append(
                    Notification(
                        id=row[0],
                        notification_type=row[1],
                        recipients=[moniker],
                        recipients_ok=[moniker],
                        recipients_failed=[],
                        sender_moniker=row[2],
                        template=row[3],
                        template_vars=row[4] or {},
                        message=_render_template(row[3], row[4] or {}),
                        data=row[6] or {},
                        urgency=NotificationUrgency(row[7]),
                        timestamp=row[8].timestamp() if row[8] else time.time(),
                        delivered_to={moniker: row[10].timestamp()} if row[10] else {},
                        read_by={moniker: row[9].timestamp()} if row[9] else {},
                        should_persist=True,
                        created_at=row[8],
                    )
                )

            return notifications
    finally:
        if should_close_conn:
            conn.close()


def get_queue(moniker: str) -> UserNotificationQueue:
    """Get the in-memory notification queue for active user sessions."""
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    with _queues_lock:
        if moniker not in _queues:
            _queues[moniker] = UserNotificationQueue()
        return _queues[moniker]


def count(moniker: str, conn: Optional[Any] = None) -> int:
    """Get total unread notification count for user (queue + database)."""
    if not moniker:
        return 0

    # In-memory queue count
    queue = get_queue(moniker)
    queue_count = queue.size()

    # Database unread count
    try:
        notifications = get_notifications(moniker, unread_only=True, conn=conn)
        db_count = len(notifications)
    except Exception:
        io.echo_traceback("bbsengine6.notify.count.100:")
        db_count = 0

    return queue_count + db_count


def get_urgent(moniker: str, conn: Optional[Any] = None) -> List[Notification]:
    """Get urgent (URGENT or CRITICAL) unread notifications for user."""
    notifications = get_notifications(moniker, unread_only=True, conn=conn)
    return [
        n
        for n in notifications
        if n.urgency in (NotificationUrgency.URGENT, NotificationUrgency.CRITICAL)
    ]


def mark_read(notification_id: int, moniker: str, conn: Optional[Any] = None) -> None:
    """Mark notification as read by user."""
    if not isinstance(notification_id, int) or notification_id <= 0:
        raise ValueError("Invalid notification_id")
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    UPDATE engine.__notify_recipient
                    SET read_at = now()
                    WHERE notify_id = %s AND recipient_moniker = %s
                """),
                (notification_id, moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def mark_delivered(
    notification_id: int, moniker: str, conn: Optional[Any] = None
) -> None:
    """Mark notification as delivered to user."""
    if not isinstance(notification_id, int) or notification_id <= 0:
        raise ValueError("Invalid notification_id")
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    UPDATE engine.__notify_recipient
                    SET delivered_at = now()
                    WHERE notify_id = %s AND recipient_moniker = %s
                """),
                (notification_id, moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def register_type(
    type_name: str,
    default_urgency: NotificationUrgency = NotificationUrgency.ROUTINE,
    max_per_hour: int = 10,
    persist_by_default: bool = True,
    conn: Optional[Any] = None,
) -> None:
    """Explicitly register a notification type with rate limits."""
    if not _validate_type_name(type_name):
        raise ValueError(f"Invalid type_name: {type_name}")
    if not isinstance(max_per_hour, int) or max_per_hour <= 0:
        raise ValueError("max_per_hour must be positive integer")

    with _types_lock:
        if type_name in _types:
            raise ValueError(f"Type {type_name} already registered")

        _types[type_name] = {
            "default_urgency": default_urgency,
            "max_per_hour": max_per_hour,
            "persist_by_default": persist_by_default,
        }

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    INSERT INTO engine.__notify_type
                    (type_name, default_urgency, max_per_user_per_hour, persist_by_default, registered_at)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (type_name) DO NOTHING
                """),
                (type_name, default_urgency.value, max_per_hour, persist_by_default),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def get_types(conn: Optional[Any] = None) -> Dict[str, Dict]:
    """Get all registered notification types and their settings."""
    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    SELECT type_name, default_urgency, max_per_user_per_hour, persist_by_default
                    FROM engine.__notify_type
                """)
            )
            rows = cur.fetchall()

            types = {}
            for row in rows:
                types[row[0]] = {
                    "default_urgency": row[1],
                    "max_per_hour": row[2],
                    "persist_by_default": row[3],
                }
            return types
    finally:
        if should_close_conn:
            conn.close()


def set_rate_limit(
    type_name: str, max_per_hour: int, conn: Optional[Any] = None
) -> None:
    """Change rate limit for a notification type at runtime."""
    if not _validate_type_name(type_name):
        raise ValueError(f"Invalid type_name: {type_name}")
    if not isinstance(max_per_hour, int) or max_per_hour <= 0:
        raise ValueError("max_per_hour must be positive integer")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    "UPDATE engine.__notify_type SET max_per_user_per_hour = %s WHERE type_name = %s"
                ),
                (max_per_hour, type_name),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def create_group(
    group_name: str,
    member_monikers: Optional[List[str]] = None,
    conn: Optional[Any] = None,
) -> None:
    """Create a new notification group."""
    if not group_name or not isinstance(group_name, str) or len(group_name) > 100:
        raise ValueError("Invalid group_name")

    if member_monikers is None:
        member_monikers = []

    # Validate all monikers
    for moniker in member_monikers:
        if not _validate_moniker(moniker):
            raise ValueError(f"Invalid moniker in group: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            for moniker in member_monikers:
                cur.execute(
                    sql.SQL("""
                        INSERT INTO engine.__notify_group (group_name, member_moniker, added_at)
                        VALUES (%s, %s, now())
                        ON CONFLICT (group_name, member_moniker) DO NOTHING
                    """),
                    (group_name, moniker),
                )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def add_to_group(group_name: str, moniker: str, conn: Optional[Any] = None) -> None:
    """Add user to group."""
    if not group_name or not isinstance(group_name, str) or len(group_name) > 100:
        raise ValueError("Invalid group_name")
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    INSERT INTO engine.__notify_group (group_name, member_moniker, added_at)
                    VALUES (%s, %s, now())
                    ON CONFLICT (group_name, member_moniker) DO NOTHING
                """),
                (group_name, moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def remove_from_group(
    group_name: str, moniker: str, conn: Optional[Any] = None
) -> None:
    """Remove user from group."""
    if not group_name or not isinstance(group_name, str) or len(group_name) > 100:
        raise ValueError("Invalid group_name")
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    "DELETE FROM engine.__notify_group WHERE group_name = %s AND member_moniker = %s"
                ),
                (group_name, moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def get_group_members(group_name: str, conn: Optional[Any] = None) -> List[str]:
    """Get all members of a group."""
    if not group_name or not isinstance(group_name, str) or len(group_name) > 100:
        raise ValueError("Invalid group_name")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    "SELECT member_moniker FROM engine.__notify_group WHERE group_name = %s"
                ),
                (group_name,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        if should_close_conn:
            conn.close()


def block(
    blocker_moniker: str, sender_moniker: str, conn: Optional[Any] = None
) -> None:
    """Block notifications from sender to blocker (one-way)."""
    if not _validate_moniker(blocker_moniker):
        raise ValueError(f"Invalid blocker_moniker: {blocker_moniker}")
    if not _validate_moniker(sender_moniker):
        raise ValueError(f"Invalid sender_moniker: {sender_moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL("""
                    INSERT INTO engine.__notify_block (blocker_moniker, sender_moniker, datecreated)
                    VALUES (%s, %s, now())
                    ON CONFLICT (blocker_moniker, sender_moniker) DO NOTHING
                """),
                (blocker_moniker, sender_moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def unblock(
    blocker_moniker: str, sender_moniker: str, conn: Optional[Any] = None
) -> None:
    """Remove a block."""
    if not _validate_moniker(blocker_moniker):
        raise ValueError(f"Invalid blocker_moniker: {blocker_moniker}")
    if not _validate_moniker(sender_moniker):
        raise ValueError(f"Invalid sender_moniker: {sender_moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    "DELETE FROM engine.__notify_block WHERE blocker_moniker = %s AND sender_moniker = %s"
                ),
                (blocker_moniker, sender_moniker),
            )
            conn.commit()
    finally:
        if should_close_conn:
            conn.close()


def is_blocked(
    sender_moniker: str, recipient_moniker: str, conn: Optional[Any] = None
) -> bool:
    """Check if sender's notifications to recipient are blocked (one-way check)."""
    if not _validate_moniker(sender_moniker):
        raise ValueError(f"Invalid sender_moniker: {sender_moniker}")
    if not _validate_moniker(recipient_moniker):
        raise ValueError(f"Invalid recipient_moniker: {recipient_moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            return _check_is_blocked(sender_moniker, recipient_moniker, cur)
    finally:
        if should_close_conn:
            conn.close()


def get_blocked(moniker: str, conn: Optional[Any] = None) -> List[str]:
    """Get list of all monikers that have blocked this user."""
    if not _validate_moniker(moniker):
        raise ValueError(f"Invalid moniker: {moniker}")

    should_close_conn = False
    if not conn:
        conn = psycopg.connect("dbname=postgres")
        should_close_conn = True

    try:
        with database.cursor(conn) as cur:
            cur.execute(
                sql.SQL(
                    "SELECT sender_moniker FROM engine.__notify_block WHERE blocker_moniker = %s"
                ),
                (moniker,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        if should_close_conn:
            conn.close()


__all__ = [
    "NotificationUrgency",
    "Notification",
    "UserNotificationQueue",
    "send",
    "get_notifications",
    "get_queue",
    "count",
    "get_urgent",
    "mark_read",
    "mark_delivered",
    "register_type",
    "get_types",
    "set_rate_limit",
    "create_group",
    "add_to_group",
    "remove_from_group",
    "get_group_members",
    "block",
    "unblock",
    "is_blocked",
    "get_blocked",
]
