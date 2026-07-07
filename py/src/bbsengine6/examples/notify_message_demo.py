# notify_message_demo.py
# Interactive two-user message system demo using bbsengine6's notify system

import argparse
import subprocess
import sys
import termios
import threading
from collections import deque
from datetime import datetime
from typing import Any, Callable, Optional

from bbsengine6 import database, member, group
from bbsengine6 import bottombar
from bbsengine6.io.echo import echo, echo_traceback
from bbsengine6.io.inputstring import inputstring
from bbsengine6.io import screen, terminal
from bbsengine6.notify import UserNotificationQueue
from bbsengine6.notify.utils import (
    AsciiValidator,  # noqa: F401  re-exported for tests
    EchoProcessor,  # noqa: F401  re-exported for tests
    TemplateEngine,
    DemoConfig,
)
from bbsengine6.notify.demo import (
    _demo_queues,
    _queues_lock,
    send_message as demo_send_message,
    pop_demo_messages,
    demo_queue_size,
)


def handle_character_input(key: str, buffer: str) -> str:
    """Process a single keystroke and return updated buffer.

    Used by test_interactive_harness.py for unit testing the input loop.
    Mirrors inputstring's key handling logic for character input, backspace,
    and escape key.
    """
    if key == "KEY_BACKSPACE":
        return buffer[:-1] if buffer else ""
    elif key == "KEY_ESC":
        return ""
    elif key.startswith("KEY_") or key in ("\x00", "\x03"):
        return buffer
    else:
        return buffer + key


def display_with_more_prompt(
    messages: list[str],
    page_size: int = 5,
    on_page_displayed: Optional[Callable[[], None]] = None,
    input_func: Optional[Callable[[str], str]] = None,
) -> bool:
    """Display messages with a more prompt for pagination."""
    if input_func is None:
        import builtins

        input_func = builtins.input

    if not messages:
        return True

    for i, message in enumerate(messages):
        echo(message)
        if (i + 1) % page_size == 0 and i + 1 < len(messages):
            if on_page_displayed:
                on_page_displayed()
            try:
                response = input_func("More? (press Enter or 'n' to abort): ")
                if response == "n":
                    return False
            except (EOFError, KeyboardInterrupt):
                return False

    return True


class MessageHandler:
    """Handles message reception and rendering for a single user."""

    _demo_queues = _demo_queues
    _queues_lock = _queues_lock

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

        if not self.args or not self.pool:
            with _queues_lock:
                if config.moniker not in _demo_queues:
                    _demo_queues[config.moniker] = deque(maxlen=100)

    def send_message(self, message: str, recipient: str) -> None:
        """Send a message to another user via the notify system."""
        try:
            was_sent = demo_send_message(
                config=self.config,
                message=message,
                recipient=recipient,
                args=self.args,
                pool=self.pool,
            )
            if was_sent:
                with self._lock:
                    self.stats["sent"] += 1
                    self.message_history.append(
                        {
                            "direction": "out",
                            "timestamp": datetime.now(),
                            "recipient": recipient,
                            "message": message,
                        }
                    )
        except (ValueError, subprocess.SubprocessError):
            with self._lock:
                self.stats["errors"] += 1
            raise

    def get_unread_messages(self) -> list[dict]:
        """Get unread messages WITHOUT marking them as read or clearing queue.

        Returns a COPY of messages in demo mode (doesn't consume from queue).
        """
        messages = []

        try:
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.cursor(conn) as cur:
                        cur.execute(
                            """
                            SELECT n.id, n.sender_moniker, n.rendered_message, n.datecreated
                            FROM engine.__notify n
                            JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                            WHERE nr.recipient_moniker = %s AND nr.dateread IS NULL
                            ORDER BY n.datecreated DESC
                            """,
                            (self.config.moniker,),
                        )
                        rows = cur.fetchall()
                        for row in rows:
                            if isinstance(row, dict):
                                messages.append(row)
                            else:
                                messages.append(
                                    {
                                        "id": row[0],
                                        "sender": row[1],
                                        "message": row[2],
                                        "timestamp": row[3],
                                    }
                                )
            else:
                with _queues_lock:
                    if self.config.moniker in _demo_queues:
                        for msg in _demo_queues[self.config.moniker]:
                            messages.append(msg)

        except Exception as e:
            echo_traceback(f"Error retrieving messages: {e}")

        return messages

    def _pop_messages(self, count: int) -> list[dict]:
        """Pop (consume) messages from demo queue (for receive_messages).

        In demo mode, this removes messages from the queue to simulate being "received".
        """
        return pop_demo_messages(self.config.moniker, count)

    def get_history(self) -> list[dict]:
        """Get local message history for this session."""
        with self._lock:
            return list(self.message_history)

    def get_stats(self) -> dict[str, int]:
        """Get message statistics."""
        with self._lock:
            return dict(self.stats)

    def resolve_recipient(self, recipient_input: str) -> list[str]:
        """Resolve recipient name(s) from input like '@bob' or '@ops_group'."""
        recipient = recipient_input.lstrip("@")

        if not recipient:
            raise ValueError("Empty recipient name")

        try:
            is_grp = group.exists(self.args, recipient, pool=self.pool)
            if is_grp:
                members = group.get_members(self.args, recipient, pool=self.pool)
                if members and len(members) > 0:
                    return members
                else:
                    raise ValueError(f"Group '{recipient}' is empty")
        except Exception:
            pass

        if self.args and self.pool:
            if not member.moniker_exists(self.args, recipient, pool=self.pool):
                raise ValueError(f"Member or group '{recipient}' not found")

        return [recipient]

    def mark_messages_as_read(self, message_ids: list[int | None]) -> None:
        """Mark messages as read in the database (no-op in demo mode)."""
        if not self.args or not self.pool or not message_ids:
            return

        valid_ids = [mid for mid in message_ids if mid is not None]
        if not valid_ids:
            return

        try:
            with database.connect(self.args, pool=self.pool) as conn:
                with database.cursor(conn) as cur:
                    for msg_id in valid_ids:
                        cur.execute(
                            """
                            UPDATE engine.__notify_recipient
                            SET dateread = now()
                            WHERE notify_id = %s AND recipient_moniker = %s
                            """,
                            (msg_id, self.config.moniker),
                        )
        except Exception as e:
            echo_traceback(f"Error marking messages as read: {e}")

    def receive_messages(self) -> list[dict]:
        """Get unread messages (does not consume from demo queue)."""
        messages = self.get_unread_messages()

        for msg in messages:
            if "direction" not in msg:
                msg["direction"] = "in"

        return messages


class NotifyMessageDemo:
    """Main demo runner for two-user interactive messaging."""

    def __init__(self, config: DemoConfig, args: Optional[Any] = None):
        self.config = config
        self.config.validate()
        self.args = args
        self.pool = None
        if args and hasattr(args, "databasename") and args.databasename:
            try:
                system_pool = database.getpool(args, dbname="postgres")
                if not database.exists(args, args.databasename, pool=system_pool):
                    echo(
                        f"Error: Database '{args.databasename}' does not exist. "
                        f"Falling back to demo mode (in-memory queues).",
                        level="error",
                    )
                    args = None
                else:
                    self.pool = database.getpool(args, dbname=args.databasename)
            except Exception as e:
                echo(
                    f"Error connecting to database: {e}. "
                    f"Falling back to demo mode (in-memory queues).",
                    level="error",
                )
                args = None

        self.handler = MessageHandler(config, args=args, pool=self.pool)

    def _handle_f2(self) -> None:
        """Handle F2 key to show unread messages."""
        echo("\n{F2} Checking messages...")
        messages = self.handler.receive_messages()

        if not messages:
            echo("No new messages.")
            return

        echo(f"You have {len(messages)} message(s):\n")
        for i, msg in enumerate(messages, 1):
            rendered = msg.get("rendered_message")
            if rendered:
                echo(f"  [{i}] {rendered}")
            else:
                sender = msg.get("sender_moniker", msg.get("sender", "unknown"))
                content = msg.get("message", "")
                echo(f"  [{i}] {sender}: {content}")
        echo("")

    def run_interactive(self) -> None:
        """Run the demo in interactive mode."""
        screen.init()

        def f2_handler(buffer, curpos, scroll_offset, max_width):
            self._handle_f2()
            return buffer, curpos, scroll_offset

        echo(f"Welcome, {self.config.moniker}!")
        echo("Commands: '@user message' to send, 'F2' to check messages, 'q' to quit")

        try:
            while True:
                try:
                    user_input = inputstring(
                        "Enter command: ",
                        timeout=0.5,
                        function_key_handlers={"KEY_F2": f2_handler},
                    )
                    if not user_input:
                        continue

                    if user_input.lower() == "q":
                        break
                    elif user_input.startswith("@"):
                        self._process_input(user_input)
                    else:
                        echo(
                            "Unknown command. Use '@user message' to send, 'F2' to check messages.",
                            level="error",
                        )
                except KeyboardInterrupt:
                    echo("\nExiting... (Ctrl+C)")
                    break
                except EOFError:
                    echo("\nExiting... (Ctrl+D)")
                    break
                except Exception as e:
                    echo(f"Error: {e}", level="error")
        finally:
            echo(
                f"{{savecursor}}{{curpos:{terminal.height()},0}}{{el}}{{reset}}{{restorecursor}}"
            )

    def _process_input(self, user_input: str) -> None:
        """Process user input for sending messages or commands.

        Supports @recipient or @group for group messaging.
        """
        # Handle stats command
        if user_input.lower() == "stats":
            self._show_stats()
            return

        # Handle message sending (@recipient or @group)
        if user_input.startswith("@"):
            parts = user_input.split(" ", 1)
            if len(parts) < 2:
                raise ValueError("Usage: @recipient message")

            recipient_input = parts[0]
            message = parts[1]

            try:
                recipients = self.handler.resolve_recipient(recipient_input)
                for recipient in recipients:
                    self.handler.send_message(message, recipient)
                    echo(f"Message sent to {recipient}")
            except ValueError:
                raise
        else:
            # Unknown command
            raise ValueError("Unknown command")

    def _show_stats(self) -> None:
        """Display message statistics."""
        stats = self.handler.get_stats()
        echo(f"Statistics: {stats}")

    def _get_unread_count(self) -> int:
        """Get count of unread messages for status bar display."""
        return len(self.handler.get_unread_messages())

    def _check_and_display_messages(self) -> None:
        """Check for unread messages and display with pagination.

        Handles page-wise marking: messages are marked as read after each
        page is fully displayed. If user aborts (presses 'n'), remaining
        messages stay unread.
        """
        all_unread = self.handler.get_unread_messages()

        if not all_unread:
            echo("No new messages.")
            return

        echo(f"You have {len(all_unread)} message(s):\n")

        page_size = 5
        displayed_count = 0
        total_displayed = 0

        for i, msg in enumerate(all_unread):
            rendered = msg.get("rendered_message")
            if rendered:
                echo(f"  [{i + 1}] {rendered}")
            else:
                sender = msg.get("sender_moniker", msg.get("sender", "unknown"))
                content = msg.get("message", "")
                echo(f"  [{i + 1}] {sender}: {content}")

            displayed_count += 1
            total_displayed += 1

            if displayed_count == page_size and i + 1 < len(all_unread):
                echo("")
                response = input(f"More? (press Enter or 'n' to abort): ")
                if response.lower() == "n":
                    echo("")
                    return
                echo("")
                displayed_count = 0

        if self.args and self.pool:
            marked_ids = [
                msg.get("id") for msg in all_unread if msg.get("id") is not None
            ]
            self.handler.mark_messages_as_read(marked_ids)
        else:
            self.handler._pop_messages(total_displayed)
        echo("")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive two-user message system demo"
    )

    parser.add_argument(
        "--user",
        default="testuser",
        help="User moniker (default: testuser)",
    )

    parser.add_argument(
        "--template",
        default=TemplateEngine.DEFAULT_TEMPLATE,
        help="Message template (default: '{sender}: {message}')",
    )

    parser.add_argument(
        "--max-messages",
        type=int,
        default=50,
        help="Maximum messages to keep in history",
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="Timeout for checking messages (seconds)",
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

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Accept any user value without database validation",
    )

    database.buildargs(parser)

    args = parser.parse_args()

    # Validate user against database unless --mock is specified
    mock_mode = args.mock
    if not mock_mode and args.databasename:
        try:
            from bbsengine6.member import moniker_exists

            system_pool = database.getpool(args, dbname="postgres")
            if database.exists(args, args.databasename, pool=system_pool):
                user_pool = database.getpool(args, dbname=args.databasename)
                exists = moniker_exists(args, args.user, pool=user_pool)
                if exists is False:
                    echo(
                        f"Error: User '{args.user}' not found in database '{args.databasename}'. "
                        f"Use --mock to bypass validation.",
                        level="error",
                    )
                    sys.exit(1)
                elif exists is None:
                    echo(
                        f"Error: Could not validate user '{args.user}'. "
                        f"Use --mock to bypass validation.",
                        level="error",
                    )
                    sys.exit(1)
        except Exception as e:
            echo(f"Error validating user: {e}", level="error")
            echo("Use --mock to bypass validation.", level="info")
            sys.exit(1)

    # Initialize screen for terminal management
    try:
        screen.init()
    except (OSError, termios.error):
        pass
    except Exception:
        pass

    # Set bottom bar with message count status
    try:
        unread_count = demo_queue_size(args.user)
        if unread_count > 0:
            bottombar.setbottombar(None, f"F2: Messages ({unread_count})")
    except Exception:
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
        echo("{decsc}{reset}{decrc}")


if __name__ == "__main__":
    main()
