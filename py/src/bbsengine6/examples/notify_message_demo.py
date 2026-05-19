# notify_message_demo.py
# Interactive two-user message system demo using bbsengine6's notify system

import argparse
import re
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from bbsengine6 import database
from bbsengine6.io.inputstring import inputstring
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
                                raise ValueError("Failed to get notify_id from database insert")

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

    def receive_messages(self) -> list[dict]:
        """Check for and return new messages from database or demo queue."""
        messages = []

        try:
            if self.args and self.pool:
                with database.connect(self.args, pool=self.pool) as conn:
                    with database.transaction(conn):
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

                                # Mark as read
                                cur.execute(
                                    """
                                    UPDATE engine.__notify_recipient
                                    SET read_at = NOW()
                                    WHERE notify_id = %s AND recipient_moniker = %s
                                    """,
                                    (notify_id, self.config.moniker),
                                )
            else:
                # Demo mode: check in-memory queue
                with MessageHandler._queues_lock:
                    queue = MessageHandler._demo_queues.get(self.config.moniker)
                    if queue:
                        while queue:
                            msg = queue.popleft()
                            messages.append(
                                {
                                    "direction": "in",
                                    "timestamp": msg["timestamp"],
                                    "sender": msg["sender"],
                                    "message": msg["message"],
                                }
                            )

            with self._lock:
                self.stats["received"] += len(messages)
                self.message_history.extend(messages)

        except Exception as e:
            print(f"Error receiving messages: {e}", file=sys.stderr)

        return messages

    def get_stats(self) -> Dict[str, int]:
        """Get message statistics."""
        with self._lock:
            return dict(self.stats)

    def get_history(self) -> list:
        """Get message history."""
        with self._lock:
            return list(self.message_history)


class NotifyMessageDemo:
    """Main demo runner for two-user interactive messaging."""

    def __init__(self, config: DemoConfig, args: Optional[Any] = None):
        self.config = config
        self.config.validate()
        self.args = args
        # Get pool if database is configured
        self.pool = None
        if args and hasattr(args, 'databasename') and args.databasename:
            try:
                self.pool = database.getpool(args, dbname=args.databasename)
            except Exception:
                # If pool initialization fails, continue in demo mode
                self.pool = None
        self.handler = MessageHandler(config, args, pool=self.pool)

    def run_interactive(self) -> None:
        """Run interactive message prompt for this user."""
        print(f"\n{'=' * 60}")
        print(f"Notify Message Demo - User: {self.config.moniker}")
        print(f"{'=' * 60}")
        print(f"Template: {self.config.template}")
        print(f"\nCommands:")
        print(f"  @<user> <message>  - Send message to user")
        print(f"  echo <text>         - Use echo command in message")
        print(f"  ?                   - Show this help")
        print(f"  q                   - Quit")
        print(f"{'=' * 60}\n")

        try:
            while True:
                # Get user input - minimal overhead, no message checking during input
                user_input = inputstring(
                    f"{self.config.moniker}> ",
                ).strip()

                if not user_input:
                    continue

                if user_input.lower() in ("q", "quit"):
                    break

                if user_input == "?":
                    self._show_help()
                    continue

                # Parse message
                try:
                    self._process_input(user_input)
                except ValueError as e:
                    print(f"Error: {e}")

        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except EOFError:
            pass
        finally:
            self._show_stats()

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

Template: {self.config.template}
Moniker: {self.config.moniker}
Echo commands: {"enabled" if self.config.enable_echo_commands else "disabled"}

Examples:
  @alice Hello there!
  @bob echo "Test message"
  @alice !echo "Current time"
"""
        print(help_text)

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
            print(f"[SENT to {recipient}] {message}")

        elif user_input == "stats":
            self._show_stats()

        else:
            raise ValueError(f"Unknown command: {user_input}. Use ? for help.")

    def _show_stats(self) -> None:
        """Display message statistics."""
        stats = self.handler.get_stats()
        print(f"\n{'=' * 60}")
        print(f"Message Statistics - {self.config.moniker}")
        print(f"{'=' * 60}")
        print(f"Sent:     {stats['sent']}")
        print(f"Received: {stats['received']}")
        print(f"Errors:   {stats['errors']}")
        print(f"{'=' * 60}\n")


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
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
