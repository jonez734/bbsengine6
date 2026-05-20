# notify/demo.py
# Functional message handling for demo mode

import threading
from collections import deque
from datetime import datetime
from typing import Optional, Any, Dict, List

from bbsengine6 import database, member, group
from bbsengine6.io.echo import echo_traceback
from ..notify.utils import AsciiValidator, TemplateEngine, EchoProcessor, DemoConfig

# Class-level in-memory queues for demo mode
_demo_queues: Dict[str, deque] = {}
_queues_lock = threading.Lock()


def validate_message(message: str, max_length: int = 500) -> None:
    """Validate message format.

    Args:
        message: Message text to validate
        max_length: Maximum allowed message length

    Raises:
        ValueError: If message is invalid
    """
    AsciiValidator.validate_or_raise(message, "message")

    if len(message) > max_length:
        raise ValueError(f"Message too long: {len(message)} > {max_length} chars")


def resolve_recipient(args: Any, pool: Any, recipient: str) -> List[str]:
    """Resolve recipient name to list of monikers.

    Handles both individual users and group names, expanding groups automatically.

    Args:
        args: Application args
        pool: Database pool
        recipient: User moniker or group name

    Returns:
        List of member monikers to send to

    Raises:
        ValueError: If recipient not found
    """
    # Demo mode: return recipient as-is
    if not args or not pool:
        return [recipient]

    # Database mode: try to expand as group first
    try:
        is_grp = group.exists(args, recipient, pool=pool)
        if is_grp:
            members = group.get_members(args, recipient, pool=pool)
            if members is not None and len(members) > 0:
                return members
            else:
                raise ValueError(f"group {recipient} is empty")

        # Not a group, check if it's a valid moniker
        if not member.moniker_exists(args, recipient, pool=pool):
            raise ValueError(f"member {recipient} not found")

        return [recipient]

    except ValueError:
        raise
    except Exception as e:
        echo_traceback(f"Error resolving recipient {recipient}: {e}")
        raise ValueError(f"Error resolving recipient {recipient}")


def send_to_demo_queue(sender: str, recipients: List[str], rendered_message: str) -> None:
    """Send message to in-memory demo queue.

    Args:
        sender: Sender moniker
        recipients: List of recipient monikers
        rendered_message: Already-rendered message text
    """
    global _demo_queues
    with _queues_lock:
        for rec in recipients:
            if rec not in _demo_queues:
                _demo_queues[rec] = deque(maxlen=100)
            _demo_queues[rec].append(
                {
                    "sender": sender,
                    "message": rendered_message,
                    "timestamp": datetime.now(),
                }
            )


def send_to_database(
    args: Any, pool: Any, config: DemoConfig, rendered_message: str, recipients: List[str]
) -> None:
    """Send message to database.

    Args:
        args: Application args
        pool: Database pool
        config: Demo configuration
        rendered_message: Already-rendered message text
        recipients: List of recipient monikers
    """
    with database.connect(args, pool=pool) as conn:
        with database.transaction(conn):
            with database.cursor(conn) as cur:
                # Insert into engine.__notify
                cur.execute(
                    """
                    INSERT INTO engine.__notify
                    (notification_type, template, rendered_message, sender_moniker, urgency)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        "demo-message",
                        config.template,
                        rendered_message,
                        config.moniker,
                        "ROUTINE",
                    ),
                )
                result_row = cur.fetchone()
                if isinstance(result_row, dict):
                    notify_id = result_row.get("id")
                else:
                    notify_id = result_row[0] if result_row else None

                if not notify_id:
                    raise ValueError("Failed to get notify_id from database insert")

                # Insert recipient entries for each recipient
                for rec in recipients:
                    cur.execute(
                        """
                        INSERT INTO engine.__notify_recipient
                        (notify_id, recipient_moniker)
                        VALUES (%s, %s)
                        """,
                        (notify_id, rec),
                    )


def send_message(
    config: DemoConfig,
    message: str,
    recipient: str,
    args: Optional[Any] = None,
    pool: Optional[Any] = None,
) -> None:
    """Send a message to a recipient (user or group).

    Validates message and recipient, then sends via database or demo queue.

    Args:
        config: Demo configuration
        message: Message text to send
        recipient: Recipient name (user moniker or group name)
        args: Optional application args
        pool: Optional database pool

    Raises:
        ValueError: If message or recipient is invalid
    """
    # Validate message
    validate_message(message)

    # Resolve recipient (expand groups)
    recipients = resolve_recipient(args, pool, recipient)

    # Process echo command if enabled
    if config.enable_echo_commands and EchoProcessor.is_echo_command(message):
        message = EchoProcessor.process_echo(message)

    # Render template
    variables = {
        "sender": config.moniker,
        "message": message,
        "timestamp": datetime.now().isoformat(),
    }
    rendered = TemplateEngine.render(config.template, variables)

    # Send to each recipient
    if args and pool:
        send_to_database(args, pool, config, rendered, recipients)
    else:
        send_to_demo_queue(config.moniker, recipients, rendered)


def get_demo_messages(moniker: str) -> List[Dict]:
    """Get all messages in demo queue for a user.

    Args:
        moniker: User moniker

    Returns:
        List of message dicts
    """
    global _demo_queues
    with _queues_lock:
        if moniker in _demo_queues:
            return list(_demo_queues[moniker])
    return []


def clear_demo_queue(moniker: str) -> None:
    """Clear demo queue for a user.

    Args:
        moniker: User moniker
    """
    global _demo_queues
    with _queues_lock:
        if moniker in _demo_queues:
            _demo_queues[moniker].clear()


__all__ = [
    "validate_message",
    "resolve_recipient",
    "send_to_demo_queue",
    "send_to_database",
    "send_message",
    "get_demo_messages",
    "clear_demo_queue",
]
