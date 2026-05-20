# notify_message_demo.py
# Interactive two-user message system demo using bbsengine6's notify system

import argparse
import re
import subprocess
import sys
import termios
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bbsengine6 import database, member
from bbsengine6.io.echo import echo, echo_traceback
from bbsengine6.io.inputchoice import inputchoice
from bbsengine6.io.inputstring import inputstring
from bbsengine6.io import screen
from bbsengine6.notify import UserNotificationQueue


class AsciiValidator:
    """Validates that input contains only printable ASCII characters."""

    # Printable ASCII range: 0x20 (space) to 0x7E (tilde)
    PRINTABLE_ASCII_MIN = 0x20
    PRINTABLE_ASCII_MAX = 0x7E

    @staticmethod
    def is_valid_char(char: str) -> bool:
        """Check if a single character is valid printable ASCII."""
        if len(char) != 1:
            return False
        code = ord(char)
        return (
            AsciiValidator.PRINTABLE_ASCII_MIN
            <= code
            <= AsciiValidator.PRINTABLE_ASCII_MAX
        )

    @staticmethod
    def is_valid_string(text: str) -> bool:
        """Check if entire string is valid printable ASCII."""
        if not text:
            return True
        return all(AsciiValidator.is_valid_char(c) for c in text)

    @staticmethod
    def validate_or_raise(text: str, context: str = "input") -> None:
        """Raise ValueError if text is not valid printable ASCII."""
        if not AsciiValidator.is_valid_string(text):
            invalid_chars = [
                (i, c, ord(c))
                for i, c in enumerate(text)
                if not AsciiValidator.is_valid_char(c)
            ]
            char_list = "; ".join(
                f"pos {i}: {repr(c)} (0x{code:02x})" for i, c, code in invalid_chars
            )
            raise ValueError(
                f"Invalid characters in {context}: {char_list}. "
                f"Only printable ASCII (0x20-0x7E) allowed."
            )


class TemplateEngine:
    """Renders message templates with variable substitution."""

    DEFAULT_TEMPLATE = "{sender}: {message}"

    @staticmethod
    def validate_template(template: str) -> None:
        """Validate template syntax and required variables."""
        # Check template length
        if len(template) > 500:
            raise ValueError(f"Template too long: {len(template)} > 500 chars")

        # Check for invalid syntax
        invalid_pattern = r"\{[^}]*[^a-zA-Z0-9_{}]\}"
        if re.search(invalid_pattern, template):
            raise ValueError("Invalid variable syntax in template")

        # Ensure required variables exist
        if "{message}" not in template:
            raise ValueError("Template must contain {message} variable")

    @staticmethod
    def render(template: str, variables: Dict[str, str]) -> str:
        """Render template with variables, safe string substitution only."""
        TemplateEngine.validate_template(template)

        # Ensure all required variables are present
        required = {"{message}"}
        for var in required:
            if var not in template:
                raise ValueError(f"Missing required variable: {var}")

        # Find all variables used in template
        variable_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        used_vars = set(re.findall(variable_pattern, template))

        # Check all used variables are provided
        for var in used_vars:
            if var not in variables:
                raise ValueError(f"Variable {{{var}}} not provided")

        # Perform safe string substitution
        result = template
        for var, value in variables.items():
            result = result.replace(f"{{{var}}}", str(value))

        return result

    @staticmethod
    def get_required_variables(template: str) -> set[str]:
        """Extract set of variable names from template."""
        variable_pattern = r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}"
        return set(re.findall(variable_pattern, template))


class EchoProcessor:
    """Processes echo commands safely."""

    ECHO_PATTERN = r"^!?echo\s+(.*)$"

    @staticmethod
    def is_echo_command(text: str) -> bool:
        """Check if text is an echo command."""
        return bool(re.match(EchoProcessor.ECHO_PATTERN, text, re.IGNORECASE))

    @staticmethod
    def process_echo(text: str) -> str:
        """Execute echo command and return output."""
        match = re.match(EchoProcessor.ECHO_PATTERN, text, re.IGNORECASE)
        if not match:
            raise ValueError("Not an echo command")

        args = match.group(1).strip()

        # Validate args are ASCII
        AsciiValidator.validate_or_raise(args, "echo args")

        try:
            # Use shell=False with split for safety
            result = subprocess.run(
                ["echo", args],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            output = result.stdout.rstrip("\n")

            # Validate output is ASCII
            AsciiValidator.validate_or_raise(output, "echo output")

            return output
        except subprocess.TimeoutExpired:
            raise ValueError("Echo command timed out")
        except Exception as e:
            raise ValueError(f"Echo command failed: {e}")


class TimestampFormatter:
    """Formats timestamps in compact format with timezone information."""

    @staticmethod
    def format_compact(dt: Any) -> str:
        """Format datetime as compact timestamp with timezone.

        Args:
            dt: datetime object (aware or naive), string, or None

        Returns:
            Compact formatted string like "2024-05-19 14:30:45 UTC" or "14:30:45 UTC" if today
        """
        if dt is None:
            return "N/A"

        # Handle string timestamps (from database)
        if isinstance(dt, str):
            try:
                # Try ISO format first (from database)
                if "T" in dt:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                else:
                    # Try standard datetime string
                    dt = datetime.fromisoformat(dt)
            except (ValueError, AttributeError):
                return dt  # Return as-is if parsing fails

        if not isinstance(dt, datetime):
            return str(dt)

        # Get timezone info
        if dt.tzinfo is None:
            # Assume UTC if naive
            tz_str = "UTC"
        else:
            # Get timezone name or offset
            tz_name = dt.tzname()
            if tz_name and len(tz_name) <= 4:
                # Use timezone name if short (e.g., UTC, PST, EST)
                tz_str = tz_name
            else:
                # Use UTC offset format (e.g., +00:00)
                offset = dt.strftime("%z")
                if offset:
                    # Format as +HH:MM
                    tz_str = f"UTC{offset[:3]}:{offset[3:]}"
                else:
                    tz_str = "UTC"

        # Check if timestamp is today
        today = datetime.now(tz=dt.tzinfo if dt.tzinfo else timezone.utc).date()
        msg_date = dt.date()

        if msg_date == today:
            # Today: show only time
            return f"{dt.strftime('%H:%M:%S')} {tz_str}"
        else:
            # Different day: show full date and time
            return f"{dt.strftime('%Y-%m-%d %H:%M:%S')} {tz_str}"


@dataclass
class DemoConfig:
    """Configuration for the message demo."""

    moniker: str
    template: str = TemplateEngine.DEFAULT_TEMPLATE
    max_messages: int = 50
    check_timeout: float = 2.0
    urgency: str = "ROUTINE"
    enable_echo_commands: bool = True
    rate_limit: int = 100  # messages per hour
    clear_prompt_on_timeout: bool = False  # False=keep visible, True=clear

    def validate(self) -> None:
        """Validate configuration."""
        if not self.moniker or len(self.moniker) > 50:
            raise ValueError(f"Invalid moniker: {self.moniker}")

        AsciiValidator.validate_or_raise(self.moniker, "moniker")
        TemplateEngine.validate_template(self.template)

        if self.max_messages < 1:
            raise ValueError(f"max_messages must be >= 1, got {self.max_messages}")

        if self.check_timeout <= 0:
            raise ValueError(f"check_timeout must be > 0, got {self.check_timeout}")

        if self.rate_limit < 1:
            raise ValueError(f"rate_limit must be >= 1, got {self.rate_limit}")

        if not isinstance(self.clear_prompt_on_timeout, bool):
            raise ValueError("clear_prompt_on_timeout must be boolean")


class MessageHandler:
    """Handles message reception and rendering for a single user."""

    # Class-level in-memory queues for demo mode (when no database)
    _demo_queues: Dict[str, deque] = {}
    _queues_lock = threading.Lock()

    def __init__(
        self,
        config: DemoConfig,
        args: Optional[Any] = None,
        pool: Optional[Any] = None,
    ):
        self.config = config
        self.args = args
        self.pool = pool
        self.notification_queue = UserNotificationQueue()
        self.message_history: deque = deque(maxlen=config.max_messages)
        self.stats = {"sent": 0, "received": 0, "errors": 0}
        self._lock = threading.Lock()

        # Initialize demo queue for this user if not using database
        if not args:
            with MessageHandler._queues_lock:
                if config.moniker not in MessageHandler._demo_queues:
                    MessageHandler._demo_queues[config.moniker] = deque(maxlen=100)

    def send_message(self, message: str, recipient: str) -> None:
        """Send a message to another user via the notify system."""
        try:
            # Validate message
            AsciiValidator.validate_or_raise(message, "message")

            if len(message) > 500:
                raise ValueError(f"Message too long: {len(message)} > 500 chars")

            # Validate recipient exists (database mode only)
            if self.args and self.pool:
                if not member.moniker_exists(self.args, recipient, pool=self.pool):
                    raise ValueError(f"member {recipient} not found")

            # Process echo command if enabled
            if self.config.enable_echo_commands and EchoProcessor.is_echo_command(
                message
            ):
                message = EchoProcessor.process_echo(message)

            # Render template
            variables = {
                "sender": self.config.moniker,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }

            rendered = TemplateEngine.render(self.config.template, variables)

            # Send via database notify system or demo queue
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
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
                                    self.config.template,
                                    rendered,
                                    self.config.moniker,
                                    "ROUTINE",
                                ),
                            )
                            result_row = cur.fetchone()
                            # bbsengine6 cursor returns dict-like rows, access by column name
                            if isinstance(result_row, dict):
                                notify_id = result_row.get("id")
                            else:
                                notify_id = result_row[0] if result_row else None

                            if not notify_id:
                                raise ValueError(
                                    "Failed to get notify_id from database insert"
                                )

                            # Insert recipient entry
                            cur.execute(
                                """
                                INSERT INTO engine.__notify_recipient
                                (notify_id, recipient_moniker)
                                VALUES (%s, %s)
                                """,
                                (notify_id, recipient),
                            )
            else:
                # Demo mode: use in-memory queue
                with MessageHandler._queues_lock:
                    if recipient not in MessageHandler._demo_queues:
                        MessageHandler._demo_queues[recipient] = deque(maxlen=100)
                    MessageHandler._demo_queues[recipient].append(
                        {
                            "sender": self.config.moniker,
                            "message": rendered,
                            "timestamp": datetime.now(),
                        }
                    )

            with self._lock:
                self.stats["sent"] += 1
                self.message_history.append(
                    {
                        "direction": "out",
                        "timestamp": datetime.now(),
                        "recipient": recipient,
                        "message": rendered,
                    }
                )

        except (ValueError, subprocess.SubprocessError):
            with self._lock:
                self.stats["errors"] += 1
            raise

    def get_unread_messages(self) -> list[dict]:
        """Get unread messages WITHOUT marking them as read.

        Returns:
            List of unread messages with notify_id for database mode.
        """
        messages = []

        try:
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.cursor(conn) as cur:
                        # Query unread messages for this user
                        cur.execute(
                            """
                            SELECT n.id, n.rendered_message, n.sender_moniker, n.datecreated
                            FROM engine.__notify n
                            JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                            WHERE nr.recipient_moniker = %s
                            AND nr.read_at IS NULL
                            AND n.notification_type = 'demo-message'
                            ORDER BY n.datecreated ASC
                            """,
                            (self.config.moniker,),
                        )

                        for row in cur.fetchall():
                            # cursor returns dict-like rows by default
                            # Use .get() with safe fallback to handle missing keys
                            if isinstance(row, dict):
                                notify_id = row.get("id")
                                rendered = row.get("rendered_message")
                                sender = row.get("sender_moniker")
                                created = row.get("datecreated")
                            else:
                                notify_id = row[0]
                                rendered = row[1]
                                sender = row[2]
                                created = row[3]

                            messages.append(
                                {
                                    "direction": "in",
                                    "timestamp": created,
                                    "sender": sender,
                                    "message": rendered,
                                    "notify_id": notify_id,
                                }
                            )
            else:
                # Demo mode: check in-memory queue (without removing)
                with MessageHandler._queues_lock:
                    queue = MessageHandler._demo_queues.get(self.config.moniker)
                    if queue:
                        # Create a copy of the queue without removing items
                        for msg in queue:
                            messages.append(
                                {
                                    "direction": "in",
                                    "timestamp": msg["timestamp"],
                                    "sender": msg["sender"],
                                    "message": msg["message"],
                                }
                            )

        except Exception as e:
            echo(f"Error getting unread messages: {e}", level="error")

        return messages

    def mark_messages_as_read(self, message_ids: list) -> None:
        """Mark specific messages as read in the database.

        Args:
            message_ids: List of notify_ids to mark as read (or count for demo mode)
        """
        if not message_ids:
            return

        try:
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.transaction(conn):
                        with database.cursor(conn) as cur:
                            for notify_id in message_ids:
                                if notify_id is not None:
                                    cur.execute(
                                        """
                                        UPDATE engine.__notify_recipient
                                        SET read_at = NOW()
                                        WHERE notify_id = %s AND recipient_moniker = %s
                                        """,
                                        (notify_id, self.config.moniker),
                                    )
            else:
                # Demo mode: remove messages from queue
                with MessageHandler._queues_lock:
                    queue = MessageHandler._demo_queues.get(self.config.moniker)
                    if queue and message_ids:
                        # Remove the first N messages (in demo mode, message_ids contains counts)
                        num_to_remove = (
                            message_ids[0] if isinstance(message_ids[0], int) else 0
                        )
                        for _ in range(num_to_remove):
                            if queue:
                                queue.popleft()

        except Exception as e:
            echo(f"Error marking messages as read: {e}", level="error")

    def receive_messages(self) -> list[dict]:
        """Check for and return new messages, marking them as read.

        DEPRECATED: This method marks all messages as read immediately.
        Use get_unread_messages() and mark_messages_as_read() instead
        for more control over when messages are marked as read.
        """
        messages = self.get_unread_messages()

        # Collect notify_ids for database mode or count for demo mode
        if self.args and self.pool:
            message_ids = [msg.get("notify_id") for msg in messages]
        else:
            message_ids = [len(messages)] if messages else []

        self.mark_messages_as_read(message_ids)

        with self._lock:
            self.stats["received"] += len(messages)
            self.message_history.extend(messages)

        return messages

    def get_stats(self) -> Dict[str, int]:
        """Get message statistics."""
        with self._lock:
            return dict(self.stats)

    def get_history(self) -> list:
        """Get message history."""
        with self._lock:
            return list(self.message_history)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Functional Helpers for Interactive Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def display_header(moniker: str, template: str) -> None:
    """Display startup header information."""
    echo(f"\n{'=' * 60}")
    echo(f"Notify Message Demo - User: {moniker}")
    echo(f"{'=' * 60}")
    echo(f"Template: {template}")
    echo(f"\nCommands:")
    echo(f"  @<user> <message>  - Send message to user")
    echo(f"  echo <text>         - Use echo command in message")
    echo(f"  ?                   - Show this help")
    echo(f"  q                   - Quit")
    echo(f"  F2                  - View unread messages")
    echo(f"{'=' * 60}\n")


def update_status_display(unread_count: int) -> None:
    """Update bottom status bar with message count.

    Args:
        unread_count: Number of unread messages (0 or more)
    """
    try:
        if unread_count > 0:
            status = f"F2: Messages ({unread_count})"
        else:
            status = ""

        screen.setbottombar("", status)
    except Exception as e:
        from bbsengine6.io.echo import echo_traceback

        echo_traceback(f"update_status_display() failed: {e}")


def display_with_more_prompt(
    messages: list[str],
    page_size: int = 5,
    on_page_displayed=None,
) -> bool:
    """Display messages with a 'more' prompt allowing abort with 'n'.

    Supports page-wise marking of items as read by calling a callback
    function after each complete page is displayed.

    Args:
        messages: List of message strings to display
        page_size: Number of messages to show per page (default: 5)
        on_page_displayed: Optional callable(page_number, messages_in_page, total_displayed)
            Called after each page is fully displayed (before more prompt).
            page_number: 1-indexed page number
            messages_in_page: List of message objects for this page (from original messages list)
            total_displayed: Total messages displayed so far

    Returns:
        True if all messages were displayed, False if user aborted with 'n'
    """
    if not messages:
        return True

    total_messages = len(messages)
    for i, message in enumerate(messages):
        echo(message)

        # Show more prompt after page_size messages, or at end if fewer messages remain
        messages_shown = i + 1
        messages_remaining = total_messages - messages_shown

        # After each complete page, call the callback to mark that page as read
        if messages_shown % page_size == 0:
            # Calculate which messages are in this page
            page_start = messages_shown - page_size
            page_end = messages_shown
            if on_page_displayed is not None:
                page_num = messages_shown // page_size
                try:
                    on_page_displayed(page_num, page_start, page_end, messages_shown)
                except Exception as e:
                    # Log but don't crash if callback fails
                    from bbsengine6.io.echo import echo_traceback

                    echo_traceback(f"on_page_displayed callback error: {e}")

        if messages_shown % page_size == 0 and messages_remaining > 0:
            try:
                # Try to use inputstring() for proper status bar updates
                # Falls back to input() if in non-TTY environment (tests, pipes)
                try:
                    response = (
                        inputchoice(
                            f"More? ({messages_remaining} remaining): ",
                            "yn",
                            default="y",
                        )
                        or ""
                    )
                except Exception as e:
                    # Fall back to input() if inputstring fails (non-TTY, test environment)
                    # This catches: termios.error, OSError, IOError, UnsupportedOperation, etc.
                    is_tty_error = (
                        isinstance(e, termios.error)
                        or "fileno" in str(e)
                        or "TTY" in str(e)
                        or "ioctl" in str(e)
                        or "pseudofile" in str(e)
                        or isinstance(e, (OSError, IOError))
                    )
                    if is_tty_error:
                        response = (
                            input(
                                f"More? ({messages_remaining} remaining, n to abort): "
                            )
                            .lower()
                            .strip()
                        )
                    else:
                        raise

                if response == "n":
                    echo("\n--- Aborted ---\n")
                    return False
            except (EOFError, KeyboardInterrupt):
                echo("\n--- Aborted ---\n")
                return False

    # After all messages displayed (last page might be incomplete)
    # Mark any remaining messages from the last incomplete page
    last_page_start = (total_messages // page_size) * page_size
    if last_page_start < total_messages and on_page_displayed is not None:
        page_num = (total_messages // page_size) + 1
        try:
            on_page_displayed(page_num, last_page_start, total_messages, total_messages)
        except Exception as e:
            from bbsengine6.io.echo import echo_traceback

            echo_traceback(f"on_page_displayed callback error on last page: {e}")

    return True


class NotifyMessageDemo:
    """Main demo runner for two-user interactive messaging."""

    def __init__(self, config: DemoConfig, args: Optional[Any] = None):
        self.config = config
        self.config.validate()
        self.args = args
        # Get pool if database is configured
        self.pool = None
        if args and hasattr(args, "databasename") and args.databasename:
            try:
                # Create a pool to the system database to check if target exists
                system_pool = database.getpool(args, dbname="postgres")

                # Check if database exists before attempting to connect
                if not database.exists(args, args.databasename, pool=system_pool):
                    echo(
                        f"Error: Database '{args.databasename}' does not exist. "
                        f"Falling back to demo mode (in-memory queues).",
                        level="error",
                    )
                else:
                    # Database exists, create pool to target database
                    self.pool = database.getpool(args, dbname=args.databasename)
            except Exception as e:
                echo(
                    f"Error checking/connecting to database: {e}. "
                    f"Falling back to demo mode (in-memory queues).",
                    level="error",
                )
                self.pool = None
        self.handler = MessageHandler(config, args, pool=self.pool)

    def run_interactive(self) -> None:
        """Run interactive message prompt with F2 notifications.

        Uses the new inputstring() function with:
        - Command history (UP/DOWN arrows)
        - Custom F2 handler for message viewing
        - Help on F1
        - Input validation
        """
        # Display header
        display_header(self.config.moniker, self.config.template)

        def handle_f2(
            buffer: str, curpos: int, scroll_offset: int, max_width: int
        ) -> tuple:
            """F2 handler: Display unread messages."""
            # Display messages directly when F2 is pressed
            self._check_and_display_messages()
            # Return unchanged buffer - user can continue editing
            return buffer, curpos, scroll_offset

        def get_help_text() -> str:
            """Generate help text for F1."""
            return f"""
Commands:
  @<user> <message>  - Send message to user
  echo <text>         - Use echo command in message
  !echo <text>        - Alternative echo syntax
  ?                   - Show this help
  q/quit              - Quit
  stats               - Show message statistics
  F2                  - View unread messages

Template: {self.config.template}
Moniker: {self.config.moniker}
Echo commands: {"enabled" if self.config.enable_echo_commands else "disabled"}
"""

        try:
            while True:
                # Update status bar with unread count
                unread_count = self._get_unread_count()
                update_status_display(unread_count)

                # Use new inputstring() with function key support
                # Note: history=False for now (InputHistory needs integration work)
                user_input = inputstring(
                    f"{self.config.moniker}> ",  # prompt (positional)
                    "",  # oldvalue (positional)
                    history=False,  # TODO: Enable once InputHistory is fully integrated
                    pagesize=10,  # Jump 10 chars with PAGE UP/DOWN
                    beep_on_error=True,  # Beep on DELETE at end
                    f1_help=get_help_text,  # F1 shows help
                    function_key_handlers={
                        "KEY_F2": handle_f2,  # F2 handler (for future expansion)
                    },
                    max_len=255,
                )

                user_input = user_input.strip()

                if not user_input:
                    continue

                if user_input.lower() in ("q", "quit"):
                    break

                if user_input == "?":
                    self._show_help()
                    continue

                try:
                    self._process_input(user_input)
                except ValueError as e:
                    echo(f"Error: {e}", level="error")

        except KeyboardInterrupt:
            echo("\n\nShutting down...")
        except EOFError:
            echo("\n\nEnd of input - exiting...")
        finally:
            self._show_stats()

    def _get_unread_count(self) -> int:
        """Query database/queue for unread message count WITHOUT marking as read."""
        try:
            if self.handler.args and self.handler.pool:
                # Database mode: count unread messages
                with database.connect(
                    self.handler.args, pool=self.handler.pool
                ) as conn:
                    with database.cursor(conn) as cur:
                        cur.execute(
                            """
                            SELECT COUNT(*) AS count
                            FROM engine.__notify n
                            JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                            WHERE nr.recipient_moniker = %s
                            AND nr.read_at IS NULL
                            AND n.notification_type = 'demo-message'
                            """,
                            (self.handler.config.moniker,),
                        )
                        result = cur.fetchone()
                        if result is None:
                            return 0

                        # bbsengine6 cursor returns dict-like rows by default
                        # Use .get() with safe fallback to handle both formats
                        if isinstance(result, dict):
                            return result.get("count", 0)
                        else:
                            return result[0]
            else:
                # Demo mode: count messages in queue
                with MessageHandler._queues_lock:
                    queue = MessageHandler._demo_queues.get(self.handler.config.moniker)
                    return len(queue) if queue else 0
        except Exception as e:
            from bbsengine6.io.echo import echo_traceback

            echo_traceback(f"_get_unread_count() failed: {e}")
            return 0

    def _get_status_bar(self, **kwargs) -> str:
        """Generate status bar text showing unread message count.

        DEPRECATED: This method is no longer called by the main loop. Instead,
        the loop calls update_status_display() directly with the unread count.

        Kept for backwards compatibility in case external code calls it.
        """
        unread = self._get_unread_count()
        if unread > 0:
            return f"F2: Messages ({unread})"
        return ""

    def _check_and_display_messages(self) -> None:
        """Retrieve and display any unread messages with more prompt.

        Messages are marked as read page-by-page as they're displayed.
        If user aborts with 'n', only displayed pages are marked as read.
        """
        messages = self.handler.get_unread_messages()

        # Always show message count summary
        message_count = len(messages)
        if message_count == 0:
            echo("\n--- No unread messages ---\n")
            return

        if message_count == 1:
            echo("\n--- 1 unread message ---\n")
        else:
            echo(f"\n--- {message_count} unread messages ---\n")

        # Prepare formatted message list with timestamps
        formatted_messages = []
        for msg in messages:
            timestamp_str = TimestampFormatter.format_compact(msg.get("timestamp"))
            formatted_messages.append(f"[{timestamp_str}] {msg['message']}")

        # Callback to mark pages as read as they're displayed
        def mark_page_as_read(page_num, page_start, page_end, total_displayed):
            """Mark messages in displayed page as read.

            Args:
                page_num: 1-indexed page number
                page_start: 0-indexed start of page in messages list
                page_end: 0-indexed exclusive end of page
                total_displayed: Total messages displayed so far
            """
            page_messages = messages[page_start:page_end]
            if not page_messages:
                return

            try:
                if self.handler.args and self.handler.pool:
                    # Database mode: mark specific messages as read
                    message_ids = [
                        msg.get("notify_id")
                        for msg in page_messages
                        if msg.get("notify_id")
                    ]
                    if message_ids:
                        self.handler.mark_messages_as_read(message_ids)
                else:
                    # Demo mode: mark messages as read (remove from queue)
                    self.handler.mark_messages_as_read([len(page_messages)])

                with self.handler._lock:
                    self.handler.stats["received"] += len(page_messages)
                    self.handler.message_history.extend(page_messages)
            except Exception as e:
                echo_traceback(f"Error marking page {page_num} as read: {e}")

        # Display messages with more prompt (5 messages per page)
        display_with_more_prompt(
            formatted_messages, page_size=5, on_page_displayed=mark_page_as_read
        )

    def _show_help(self) -> None:
        """Display help information."""
        help_text = f"""
Commands:
  @<user> <message>  - Send message to user
  echo <text>         - Use echo command in message
  !echo <text>        - Alternative echo syntax
  ?                   - Show this help
  q/quit              - Quit
  stats               - Show message statistics
  F2                  - View unread messages

Template: {self.config.template}
Moniker: {self.config.moniker}
Echo commands: {"enabled" if self.config.enable_echo_commands else "disabled"}

Examples:
   @alice Hello there!
   @bob echo "Test message"
   @alice !echo "Current time"
"""
        echo(help_text)

    def _process_input(self, user_input: str) -> None:
        """Process user input."""
        if user_input.startswith("@"):
            # Send message
            parts = user_input.split(None, 1)
            if len(parts) < 2:
                raise ValueError("Usage: @<user> <message>")

            recipient = parts[0][1:]  # Remove @
            message = parts[1]

            self.handler.send_message(message, recipient)
            timestamp_str = TimestampFormatter.format_compact(datetime.now())
            echo(f"[{timestamp_str}] [SENT to {recipient}] {message}")

        elif user_input == "stats":
            self._show_stats()

        else:
            raise ValueError(f"Unknown command: {user_input}. Use ? for help.")

    def _show_stats(self) -> None:
        """Display message statistics."""
        stats = self.handler.get_stats()
        echo(f"\n{'=' * 60}")
        echo(f"Message Statistics - {self.config.moniker}")
        echo(f"{'=' * 60}")
        echo(f"Sent:     {stats['sent']}")
        echo(f"Received: {stats['received']}")
        echo(f"Errors:   {stats['errors']}")
        echo(f"{'=' * 60}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive message system demo using notify"
    )
    parser.add_argument(
        "--user", required=True, help="Username/moniker for this instance"
    )
    parser.add_argument(
        "--template",
        default=TemplateEngine.DEFAULT_TEMPLATE,
        help="Custom message template",
    )
    parser.add_argument(
        "--max-messages", type=int, default=50, help="Max messages to keep in history"
    )
    parser.add_argument(
        "--timeout", type=float, default=2.0, help="Notification check timeout"
    )
    parser.add_argument(
        "--no-echo",
        action="store_true",
        help="Disable echo command processing",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    # Add database arguments (--databasename, --databasehost, --databaseport, etc.)
    database.buildargs(parser)

    args = parser.parse_args()

    # Initialize screen for bottom bar support (prevents scrolling)
    try:
        screen.init()
    except (OSError, termios.error):
        # Silently ignore if not a TTY (e.g., in tests or piped input)
        pass
    except Exception:
        # Silently continue on other errors
        pass

    try:
        try:
            config = DemoConfig(
                moniker=args.user,
                template=args.template,
                max_messages=args.max_messages,
                check_timeout=args.timeout,
                enable_echo_commands=not args.no_echo,
            )

            # Use args as database connection parameters if database name was specified
            # Otherwise use None for demo mode (in-memory queues)
            db_args = args if args.databasename else None

            demo = NotifyMessageDemo(config, db_args)
            demo.run_interactive()

        except ValueError as e:
            echo(f"Configuration error: {e}", level="error")
            sys.exit(1)
        except Exception as e:
            echo(f"Error: {e}", level="error")
            sys.exit(1)
    finally:
        # Reset terminal to clean state: save cursor, reset, restore cursor
        echo("{decsc}{reset}{decrc}")


if __name__ == "__main__":
    main()
