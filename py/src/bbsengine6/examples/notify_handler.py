"""
notify_handler.py - Functional message handling for notify system.

Provides flat, functional operations for:
- Message sending with recipient validation
- Recipient resolution (user or group expansion)
- Message statistics tracking
- History management
"""

from bbsengine6 import database, group, member
from bbsengine6.io.echo import echo_traceback


def validate_message(message: str, max_length: int = 500) -> None:
    """Validate message format.

    Args:
        message: Message text to validate
        max_length: Maximum allowed message length (default 500)

    Raises:
        ValueError: If message is invalid
    """
    from notify_message_demo import AsciiValidator

    AsciiValidator.validate_or_raise(message, "message")

    if len(message) > max_length:
        raise ValueError(f"Message too long: {len(message)} > {max_length} chars")


def resolve_recipient(args, pool, recipient: str) -> list[str]:
    """Resolve recipient name to list of monikers.

    Handles both individual users and group names, expanding groups automatically.

    Args:
        args: Application args
        pool: Database pool (optional for database mode)
        recipient: User moniker or group name

    Returns:
        list[str]: List of member monikers to send to

    Raises:
        ValueError: If recipient not found or invalid

    Examples:
        >>> resolve_recipient(args, pool, "alice")
        ["alice"]
        >>> resolve_recipient(args, pool, "ops")
        ["alice", "bob", "charlie"]  # Expands ops group
    """
    # Demo mode: return recipient as-is
    if not args or not pool:
        return [recipient]

    # Database mode: try to expand as group first
    try:
        # Check if it's a group
        is_group = group.exists(args, recipient, pool=pool)
        if is_group:
            # Get all members of the group
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


def insert_message_to_db(args, pool, notify_id: int, recipient: str, conn=None) -> bool:
    """Insert message recipient into database.

    Args:
        args: Application args
        pool: Database pool
        notify_id: ID of the message in engine.__notify
        recipient: Recipient moniker
        conn: Optional existing connection to reuse

    Returns:
        bool: True if successful, False on error

    Raises:
        ValueError: If recipient is invalid
    """
    if not notify_id or not recipient:
        return False

    # Validate recipient exists
    if not member.moniker_exists(args, recipient, pool=pool):
        raise ValueError(f"member {recipient} not found")

    try:
        with database.cursor(conn or database.connect(args, pool=pool)) as cur:
            cur.execute(
                "INSERT INTO engine.__notify_recipient (notify_id, recipient_moniker) "
                "VALUES (%s, %s)",
                (notify_id, recipient),
            )
        return True
    except Exception:
        echo_traceback("bbsengine6.examples.notify_handler.insert_message_to_db.100:")
        return False


def send_message(args, pool, config, message: str, recipient: str, conn=None) -> None:
    """Send a message to a recipient (user or group).

    Validates message and recipient, then sends via database or demo queue.

    Args:
        args: Application args
        pool: Database pool
        config: DemoConfig with template and other settings
        message: Message text to send
        recipient: Recipient name (user moniker or group name)
        conn: Optional existing connection

    Raises:
        ValueError: If message or recipient is invalid
    """
    from notify_message_demo import TemplateEngine, EchoProcessor

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
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    rendered = TemplateEngine.render(config.template, variables)

    # Send to each recipient
    if args and pool:
        # Database mode: insert into database
        with database.connect(args, pool=pool) as db_conn:
            with database.transaction(db_conn):
                with database.cursor(db_conn) as cur:
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
                            rendered,
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
                            "INSERT INTO engine.__notify_recipient "
                            "(notify_id, recipient_moniker) VALUES (%s, %s)",
                            (notify_id, rec),
                        )
    else:
        # Demo mode: use in-memory queue
        from notify_message_demo import MessageHandler

        with MessageHandler._queues_lock:
            for rec in recipients:
                if rec not in MessageHandler._demo_queues:
                    from collections import deque

                    MessageHandler._demo_queues[rec] = deque(maxlen=100)
                MessageHandler._demo_queues[rec].append(
                    {
                        "message": rendered,
                        "sender": config.moniker,
                        "timestamp": __import__("datetime").datetime.now(),
                    }
                )
