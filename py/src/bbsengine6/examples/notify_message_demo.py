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

from bbsengine6 import database, member, group
from bbsengine6.io.echo import echo, echo_traceback
from bbsengine6.io.inputchoice import inputchoice
from bbsengine6.io.inputstring import inputstring
from bbsengine6.io import screen
from bbsengine6.notify import UserNotificationQueue
from bbsengine6.notify.utils import (
    AsciiValidator,
    TemplateEngine,
    EchoProcessor,
    TimestampFormatter,
    DemoConfig,
)


def display_with_more_prompt(messages: list[str], page_size: int = 5) -> bool:
    """Display messages with a more prompt for pagination."""
    if not messages:
        return True
    
    for i, message in enumerate(messages):
        echo(message)
        if (i + 1) % page_size == 0 and i + 1 < len(messages):
            try:
                response = input("More? (press Enter or 'n' to abort): ")
                if response.lower() == 'n':
                    return False
            except (EOFError, KeyboardInterrupt):
                return False
    
    return True


class MessageHandler:
    """Handles message reception and rendering for a single user."""

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

        if not self.args or not self.pool:
            with MessageHandler._queues_lock:
                if config.moniker not in MessageHandler._demo_queues:
                    MessageHandler._demo_queues[config.moniker] = deque(maxlen=100)

    def send_message(self, message: str, recipient: str) -> None:
        """Send a message to another user via the notify system."""
        try:
            AsciiValidator.validate_or_raise(message, "message")

            if len(message) > 500:
                raise ValueError(f"Message too long: {len(message)} > 500 chars")

            if self.args and self.pool:
                if not member.moniker_exists(self.args, recipient, pool=self.pool):
                    raise ValueError(f"member {recipient} not found")

            if self.config.enable_echo_commands and EchoProcessor.is_echo_command(message):
                message = EchoProcessor.process_echo(message)

            variables = {
                "sender": self.config.moniker,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }

            rendered = TemplateEngine.render(self.config.template, variables)

            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.transaction(conn):
                        with database.cursor(conn) as cur:
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
                            if isinstance(result_row, dict):
                                notify_id = result_row.get("id")
                            else:
                                notify_id = result_row[0] if result_row else None

                            if not notify_id:
                                raise ValueError("Failed to get notify_id from database insert")

                            cur.execute(
                                """
                                INSERT INTO engine.__notify_recipient
                                (notify_id, recipient_moniker)
                                VALUES (%s, %s)
                                """,
                                (notify_id, recipient),
                            )
            else:
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
        """Get unread messages WITHOUT marking them as read."""
        messages = []

        try:
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.cursor(conn) as cur:
                        cur.execute(
                            """
                            SELECT id, sender_moniker, rendered_message, created_at
                            FROM engine.__notify_recipient
                            WHERE recipient_moniker = %s AND is_read = false
                            ORDER BY created_at DESC
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
                with MessageHandler._queues_lock:
                    if self.config.moniker in MessageHandler._demo_queues:
                        for msg in MessageHandler._demo_queues[self.config.moniker]:
                            messages.append(msg)

        except Exception as e:
            echo_traceback(f"Error retrieving messages: {e}")

        return messages

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
        recipient = recipient_input.lstrip('@')
        
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
        except:
            pass
        
        if self.args and self.pool:
            if not member.moniker_exists(self.args, recipient, pool=self.pool):
                raise ValueError(f"Member or group '{recipient}' not found")
        
        return [recipient]

    def mark_messages_as_read(self, message_ids: list[int]) -> None:
        """Mark messages as read in the database."""
        if not self.args or not self.pool or not message_ids:
            return
        
        try:
            with database.connect(self.args, pool=self.pool) as conn:
                with database.cursor(conn) as cur:
                    for msg_id in message_ids:
                        cur.execute(
                            """
                            UPDATE engine.__notify_recipient
                            SET is_read = true
                            WHERE id = %s
                            """,
                            (msg_id,),
                        )
        except Exception as e:
            echo_traceback(f"Error marking messages as read: {e}")

    def receive_messages(self) -> list[dict]:
        """Get unread messages and mark them as read."""
        messages = self.get_unread_messages()
        
        for msg in messages:
            if 'direction' not in msg:
                msg['direction'] = 'in'
        
        if messages and self.args and self.pool:
            message_ids = [msg.get('id') for msg in messages if 'id' in msg]
            if message_ids:
                self.mark_messages_as_read(message_ids)
        
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

    def run_interactive(self) -> None:
        """Run the demo in interactive mode."""
        echo(f"Welcome, {self.config.moniker}!")
        echo(
            "Commands: '@user message' to send, 'F2' to check messages, 'q' to quit"
        )
        
        while True:
            try:
                user_input = inputstring("Enter command: ", timeout=0.5)
                if not user_input:
                    continue
                
                if user_input.lower() == 'q':
                    break
                elif user_input.startswith('@'):
                    self._process_input(user_input)
                else:
                    echo("Unknown command", level="error")
            except KeyboardInterrupt:
                break
            except Exception as e:
                echo(f"Error: {e}", level="error")

    def _process_input(self, user_input: str) -> None:
        """Process user input for sending messages or commands."""
        # Handle stats command
        if user_input.lower() == 'stats':
            self._show_stats()
            return
        
        # Handle message sending (@recipient message)
        if user_input.startswith('@'):
            parts = user_input.split(' ', 1)
            if len(parts) < 2:
                raise ValueError("Usage: @recipient message")
            
            recipient_input = parts[0]
            message = parts[1]
            
            try:
                recipients = self.handler.resolve_recipient(recipient_input)
                for recipient in recipients:
                    self.handler.send_message(message, recipient)
                    echo(f"Message sent to {recipient}")
            except ValueError as e:
                raise
        else:
            # Unknown command
            raise ValueError("Unknown command")

    
    def _show_stats(self) -> None:
        """Display message statistics."""
        stats = self.handler.get_stats()
        echo(f"Statistics: {stats}")


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

    database.buildargs(parser)

    args = parser.parse_args()

    try:
        screen.init()
    except (OSError, termios.error):
        pass
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
