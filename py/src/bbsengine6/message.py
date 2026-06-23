# message.py
# Unified message system with channel-based pub/sub and persistence

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from psycopg import sql

from . import database, io
from .database import getpool

logger = logging.getLogger(__name__)

_message_enabled: bool = True


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


def _resolve_db(database: Optional[str] = None) -> str:
    return database if database is not None else _default_db()


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
        Message ID
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
                INSERT INTO engine.__message 
                (channel, sender_moniker, content, data, urgency, template, template_vars)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (channel, sender_moniker, content, data, urgency, template, template_vars),
            )
            message_id = cur.fetchone()[0]
            
            if recipient_monikers:
                for recipient in recipient_monikers:
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
                messages.append({
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
                })
            
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
) -> int:
    """Get count of unread messages for a user.
    
    Args:
        moniker: User's moniker
        database: Database name
    
    Returns:
        Count of unread messages
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
                SELECT COUNT(*) FROM engine.__message_recipient
                WHERE recipient_moniker = %s AND status = 'pending'
                """,
                (moniker,),
            )
            return cur.fetchone()[0]


def deliver_pending_on_connect(
    moniker: str,
    database: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Deliver all pending messages to user on connect.
    
    Args:
        moniker: User's moniker
        database: Database name
    
    Returns:
        List of pending messages
    """
    if not _message_enabled:
        return []
    
    messages = get_pending_messages(moniker, database=database)
    
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
                {"id": row[0], "name": row[1], "description": row[2], "datecreated": row[3]}
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
    curly_vars = re.findall(r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}', content)
    dollar_vars = re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', content)
    
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
        template: Template to validate
    
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
    
    dollar_open = len(re.findall(r'\$[a-zA-Z_]', template))
    dollar_close = template.count("}")
    if dollar_open != 0 and dollar_open != dollar_close:
        errors.append(f"Unmatched $ variables: {dollar_open} open, {dollar_close} close")
    
    invalid_vars = re.findall(r'\{[^a-zA-Z_]', template)
    if invalid_vars:
        errors.append(f"Invalid variable syntax: {invalid_vars}")
    
    return len(errors) == 0, errors


