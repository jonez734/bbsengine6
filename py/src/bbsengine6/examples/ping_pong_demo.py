#!/usr/bin/env python3
# ping_pong_demo.py
# Interactive ping/pong message exchange demo using getch() idle loop notification detection
# Thread-safe implementation with proper synchronization and graceful shutdown

import argparse
import atexit
import os
import signal
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Deque, List, Optional, Union

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bbsengine6 import notify
    from bbsengine6.io.echo import echo
    from bbsengine6.io.getch import getch_str
    from bbsengine6.member import _threadlocal
    from bbsengine6.notify import Notification, NotificationUrgency
except ImportError as e:
    print(f"Error: Failed to import bbsengine6 modules: {e}")
    print("Make sure bbsengine6 is installed and in your Python path")
    sys.exit(1)

# Configuration - customize game behavior
class Config:
    """Configuration settings for ping/pong demo."""
    MAX_ROUNDS = 5
    GETCH_TIMEOUT = 2.0
    MESSAGE_LOG_SIZE = 100  # Maximum number of messages to keep in memory
    THREAD_TIMEOUT = 10.0  # Maximum time to wait for thread shutdown


# Constants (legacy aliases for backward compatibility)
MAX_ROUNDS = Config.MAX_ROUNDS
GETCH_TIMEOUT = Config.GETCH_TIMEOUT

# Thread-safe synchronization primitives
exit_event = threading.Event()  # Thread-safe flag for graceful shutdown
output_lock = threading.Lock()  # Synchronize print statements
message_log_lock = threading.Lock()  # Synchronize message_log access
round_counter_lock = threading.Lock()  # Synchronize round counter across threads

# Track active threads for cleanup
active_threads = []
active_threads_lock = threading.Lock()

# Shared round counter across all players
shared_rounds = {"alice": 0, "bob": 0}


def setup_notifications() -> bool:
    """Register notification types for the demo.

    Note: This demo uses the in-memory notification queue system.
    The notification types are registered locally without requiring a database.
    """
    try:
        # Register types without requiring database connection
        # For demo purposes, we'll use the _types dict directly
        from bbsengine6.notify import _types, _types_lock

        with _types_lock:
            _types["ping_message"] = {
                "default_urgency": NotificationUrgency.ROUTINE,
                "max_per_hour": 100,
                "persist_by_default": False,
            }
            _types["pong_message"] = {
                "default_urgency": NotificationUrgency.ROUTINE,
                "max_per_hour": 100,
                "persist_by_default": False,
            }

        with output_lock:
            echo("✓ Notification types registered (in-memory)")
        return True
    except (AttributeError, KeyError, TypeError) as e:
        # AttributeError: _types or _types_lock don't exist
        # KeyError: Error accessing notification type dictionary
        # TypeError: Type mismatch in registration
        with output_lock:
            echo(f"❌ Failed to register notifications: {e}")
        return False
    except ImportError as e:
        # Missing notify module or dependencies
        with output_lock:
            echo(f"❌ Failed to import notify module: {e}")
        return False


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("clear" if os.name == "posix" else "cls")


def display_menu(
    moniker: str, round_num: int, status: str, message_log: Union[List[str], Deque[str]]
) -> None:
    """Display the game menu and message log (with output synchronization)."""
    with output_lock:
        clear_screen()
        echo("═" * 60)
        echo(f"    PING-PONG DEMO (Moniker: {moniker.upper()})")
        echo("═" * 60)
        echo(f"Round: {round_num}/{MAX_ROUNDS} | Status: {status}")
        echo()
        echo("(P)ing / (C)heck / (Q)uit / [ESC] to exit")
        echo()
        echo("─" * 60)
        echo("MESSAGE LOG:")

        with message_log_lock:
            if message_log:
                # Show last 8 messages (works with both list and deque)
                log_items = list(message_log)[-8:]
                for msg in log_items:
                    echo(f"  {msg}")
            else:
                echo("  [Awaiting first message...]")

        echo("─" * 60)

        # Show queue status
        try:
            queue = notify.get_queue(moniker)
            if queue:
                all_notifs = queue.get_all()
                count = len(all_notifs)
                echo(f"Queue Status: {count} pending notification(s)")
            else:
                echo("Queue Status: Not initialized")
        except Exception as e:
            echo(f"Queue Status: Error - {e}")

        echo("═" * 60)


def _sanitize_text(text: str) -> str:
    """Remove terminal control characters from text for safe display.
    
    This prevents terminal escape sequences or control characters from
    breaking the UI or causing unexpected behavior. Uses aggressive
    filtering to keep only printable ASCII characters and basic whitespace.
    
    Args:
        text: Input text potentially containing control characters
        
    Returns:
        Sanitized text with only safe, printable characters
    """
    return ''.join(c for c in text if c.isprintable() or c in '\t ')


def send_ping(from_moniker: str, round_num: int) -> bool:
    """Send a ping/pong notification with comprehensive error handling."""
    to_moniker = "bob" if from_moniker == "alice" else "alice"

    # Determine message type and word
    msg_type = "pong_message" if from_moniker == "bob" else "ping_message"
    msg_word = "PONG" if from_moniker == "bob" else "PING"
    # Sanitize moniker to prevent terminal control character injection
    safe_moniker = _sanitize_text(from_moniker)
    msg_text = f"{msg_word} #{round_num + 1} from {safe_moniker}"

    # Create a proper Notification object for the demo
    try:
        notification = Notification(
            id=round_num,
            notification_type=msg_type,
            recipients=[to_moniker],
            recipients_ok=[to_moniker],
            recipients_failed=[],
            sender_moniker=from_moniker,
            template="default",
            template_vars={},
            message=msg_text,
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=time.time(),
        )
    except Exception as e:
        # Catch any unexpected exceptions from Notification creation
        with output_lock:
            echo(f"❌ Unexpected error creating notification: {e}")
            echo("Press Enter to continue...")
            input()
        return False

    # Try to add to recipient's queue (atomic operation)
    # This approach avoids race condition of check-then-use
    try:
        recipient_queue = notify.get_queue(to_moniker)
        if recipient_queue is None:
            raise RuntimeError(f"{to_moniker} is not logged in")
        recipient_queue.put(notification)

        with output_lock:
            echo(f"✓ Sent {msg_word} #{round_num + 1} to {to_moniker}")
        time.sleep(0.5)
        return True

    except (RuntimeError, AttributeError, TypeError) as e:
        error_str = str(e).lower()
        with output_lock:
            echo(f"❌ ERROR: Failed to send to {to_moniker}: {e}")

            if "not logged in" in error_str:
                echo(f"   → {to_moniker} is not currently available")
            elif "rate limit" in error_str:
                echo("   → You've sent too many messages too quickly")
                echo("   → Please wait a moment before sending again")
            elif "blocked" in error_str:
                echo(f"   → {to_moniker} has blocked your messages")
            elif "not registered" in error_str:
                echo(f"   → Notification type not registered")

            echo("Press Enter to continue...")
            input()
        return False


def check_and_display_queue(moniker: str, message_log: Union[List[str], Deque[str]]) -> None:
    """Check and display all pending notifications (with output synchronization).
    
    WARNING: This operation is DESTRUCTIVE - all retrieved notifications are removed
    from the queue. Messages cannot be retrieved again unless the sender resends them.
    This is intentional design: checking queue consumes messages automatically.
    See README_PING_PONG.md for behavior documentation.
    
    Args:
        moniker: Member whose queue to check
        message_log: Shared message log to append notifications to
    """
    try:
        queue = notify.get_queue(moniker)
        if queue is None:
            with output_lock:
                echo(f"❌ Queue not found for {moniker}")
                echo("Press Enter to continue...")
                input()
            return

        all_notifs = queue.get_all()

        if not all_notifs:
            with output_lock:
                echo(f"✓ No pending notifications for {moniker}")
            time.sleep(1)
            return

        with output_lock:
            echo(f"\n─── Pending Notifications for {moniker} ───")
            for notif in all_notifs:
                try:
                    msg = getattr(notif, "message", None) or "No message"
                    urgency = getattr(notif, "urgency", None) or "ROUTINE"
                    timestamp = getattr(notif, "timestamp", None) or "unknown"
                    echo(f"[{urgency:8}] {timestamp} | {msg}")

                    with message_log_lock:
                        message_log.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
                        )
                except AttributeError as e:
                    echo(f"⚠ Malformed notification: {e}")

            echo("──────────────────────────────────────────")
            echo("Press Enter to continue...")
            input()

    except Exception as e:
        with output_lock:
            echo(f"❌ ERROR checking queue: {e}")
            echo("Press Enter to continue...")
            input()


def player_loop(moniker: str) -> None:
    """Main game loop for a player (alice or bob) - fully thread-safe."""
    # Set thread-local moniker (simulates logged-in member)
    _threadlocal.moniker = moniker

    # Use deque with max size for automatic log rotation
    message_log = deque(maxlen=Config.MESSAGE_LOG_SIZE)

    try:
        with output_lock:
            echo(f"\n✓ {moniker.upper()} initialized (moniker={moniker})")
        time.sleep(1)

        while True:
            # Get current round number atomically
            with round_counter_lock:
                round_num = shared_rounds[moniker]
                if round_num >= MAX_ROUNDS:
                    break
            
            if exit_event.is_set():
                break

            status = "Waiting for input or notification... (Press F2 to check)"
            display_menu(moniker, round_num, status, message_log)

            try:
                # getch() automatically checks notifications and emits bell
                key = getch_str(timeout=GETCH_TIMEOUT)

                # Check for exit signal between iterations
                if exit_event.is_set():
                    break

                # Handle no input (timeout)
                if key is None:
                    continue

                # Normalize key input
                key_upper = key.upper() if isinstance(key, str) else ""

                # ESC - exit immediately (both players)
                # getch_str() returns "KEY_ESC" for the escape key
                if key_upper == "KEY_ESC":
                    exit_event.set()
                    with output_lock:
                        echo(f"\n✓ {moniker.upper()}: ESC pressed - exiting demo")
                    time.sleep(0.5)
                    break

                # Q - quit local player
                elif key_upper == "Q":
                    with output_lock:
                        echo(f"\n✓ {moniker.upper()}: Quit")
                    time.sleep(0.5)
                    break

                # P - send ping/pong
                elif key_upper == "P":
                    if send_ping(moniker, round_num):
                        with round_counter_lock:
                            shared_rounds[moniker] += 1
                        msg_word = "PONG" if moniker == "bob" else "PING"
                        with message_log_lock:
                            message_log.append(
                                f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Sent {msg_word} #{round_num + 1}"
                            )

                # C - check and display notifications
                elif key_upper == "C":
                    check_and_display_queue(moniker, message_log)

                # F2 is handled by getch() internally - it shows notifications
                # but we also offer the 'C' command for explicit checking

            except KeyboardInterrupt:
                with output_lock:
                    echo(f"\n⚠ {moniker.upper()}: Interrupted")
                exit_event.set()
                break
            except Exception as e:
                with output_lock:
                    echo(f"❌ {moniker.upper()}: Error processing input: {e}")
                time.sleep(0.5)
                continue

        # End of rounds
        with round_counter_lock:
            final_round = shared_rounds[moniker]
        if final_round >= MAX_ROUNDS and not exit_event.is_set():
            with output_lock:
                echo(f"\n✓ {moniker.upper()}: Completed {MAX_ROUNDS} rounds!")
            time.sleep(1)

    except Exception as e:
        with output_lock:
            echo(f"❌ {moniker.upper()}: Unexpected error: {e}")
    finally:
        with output_lock:
            echo(f"\n✓ {moniker.upper()}'s game ended")


def signal_handler(signum: int, frame) -> None:
    """Handle SIGINT (CTRL+C) gracefully."""
    with output_lock:
        echo("\n\n⚠ Received interrupt signal - initiating graceful shutdown...")
    exit_event.set()


def cleanup_threads() -> None:
    """Cleanup function called on exit."""
    with output_lock:
        echo("\n✓ Cleanup: Waiting for threads to finish...")

    # Set exit event in case it wasn't already set
    exit_event.set()

    # Wait for all active threads
    with active_threads_lock:
        for thread in active_threads:
            if thread.is_alive():
                with output_lock:
                    echo(f"✓ Cleanup: Waiting for {thread.name}... (max {Config.THREAD_TIMEOUT}s)")
                thread.join(timeout=Config.THREAD_TIMEOUT)
                if thread.is_alive():
                    with output_lock:
                        echo(f"⚠ Cleanup: {thread.name} did not exit cleanly")


def run_single_player(moniker: str) -> int:
    """Run the demo as a single player (designed for separate terminal instances).
    
    Args:
        moniker: Player name (any custom username)
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Register cleanup function to run on exit
    atexit.register(cleanup_threads)

    with output_lock:
        echo("\n╔════════════════════════════════════════════════════════════╗")
        echo("║  BBSENGINE6 PING-PONG DEMO - SINGLE PLAYER                 ║")
        echo("║  Player: " + moniker.upper().ljust(45) + "║")
        echo("║  Run in separate terminals with different --user names      ║")
        echo("╚════════════════════════════════════════════════════════════╝\n")

        echo("This instance is running as: {level.ok}" + moniker.upper() + "{/all}\n")
        echo("To play with another player:")
        echo("  • In another terminal, run:")
        echo(f"    python -m bbsengine6.examples.ping_pong_demo --user <other_player>\n")
        echo("For full documentation, see: README_PING_PONG.md\n")

        echo("Press Enter to start...")
        input()

    # Setup notification types
    if not setup_notifications():
        with output_lock:
            echo("\nFailed to setup notifications. Exiting.")
        return 1

    # Create a single player thread
    player_thread = threading.Thread(
        target=player_loop, args=(moniker,), daemon=False, name=moniker.capitalize()
    )

    # Track active threads
    with active_threads_lock:
        active_threads.append(player_thread)

    try:
        player_thread.start()

        # Wait for thread to complete
        with output_lock:
            echo(f"✓ {moniker.upper()} game started (max {Config.THREAD_TIMEOUT}s)...\n")

        player_thread.join(timeout=Config.THREAD_TIMEOUT)

        # Check if thread is still alive
        if player_thread.is_alive():
            with output_lock:
                echo("⚠ Warning: Player thread did not exit cleanly")
            return 1

    except KeyboardInterrupt:
        with output_lock:
            echo("\n\n⚠ Demo interrupted - cleaning up...")
        exit_event.set()
        player_thread.join(timeout=Config.THREAD_TIMEOUT)
        return 130

    except Exception as e:
        with output_lock:
            echo(f"\n❌ Error running demo: {e}")
        return 1

    with output_lock:
        echo("\n╔════════════════════════════════════════════════════════════╗")
        echo("║  Demo Complete!                                            ║")
        echo("║                                                            ║")
        echo("║  You've seen:                                              ║")
        echo("║    ✓ getch() notification checking                         ║")
        echo("║    ✓ Thread-local member isolation                         ║")
        echo("║    ✓ Per-member notification queues                        ║")
        echo("║    ✓ Multi-user concurrent messaging                       ║")
        echo("║    ✓ Error handling for edge cases                         ║")
        echo("║                                                            ║")
        echo("║  See README_PING_PONG.md for more information              ║")
        echo("╚════════════════════════════════════════════════════════════╝\n")

    return 0


def run_two_players() -> int:
    """Run the demo with two built-in players (alice and bob) in same terminal.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Register cleanup function to run on exit
    atexit.register(cleanup_threads)

    with output_lock:
        echo("\n╔════════════════════════════════════════════════════════════╗")
        echo("║  BBSENGINE6 PING-PONG DEMO - TWO PLAYERS                   ║")
        echo("║  Demonstrates getch() idle loop notification detection      ║")
        echo("║  with multi-member per-machine support                      ║")
        echo("╚════════════════════════════════════════════════════════════╝\n")

        echo("This demo shows:")
        echo("  • Two concurrent players (alice and bob) on same machine")
        echo("  • Thread-local moniker isolation for per-member queues")
        echo("  • getch() integration for automatic notification detection")
        echo("  • Bell emission when notifications arrive")
        echo("  • Comprehensive error handling for failure scenarios")
        echo("\nFor full documentation, see: README_PING_PONG.md\n")

        echo("Press Enter to start...")
        input()

    # Setup notification types
    if not setup_notifications():
        with output_lock:
            echo("\nFailed to setup notifications. Exiting.")
        return 1

    with output_lock:
        echo("\nStarting two concurrent player threads...")
        echo("(Run this script in two separate terminals for full interactivity)")
    time.sleep(1)

    # Create threads for alice and bob
    alice_thread = threading.Thread(
        target=player_loop, args=("alice",), daemon=False, name="Alice"
    )
    bob_thread = threading.Thread(
        target=player_loop, args=("bob",), daemon=False, name="Bob"
    )

    # Track active threads
    with active_threads_lock:
        active_threads.append(alice_thread)
        active_threads.append(bob_thread)

    try:
        alice_thread.start()
        bob_thread.start()

        # Wait for both threads to complete
        with output_lock:
            echo(f"✓ Waiting for player threads (max {Config.THREAD_TIMEOUT}s)...")

        alice_thread.join(timeout=Config.THREAD_TIMEOUT)
        bob_thread.join(timeout=Config.THREAD_TIMEOUT)

        # Check if threads are still alive
        if alice_thread.is_alive() or bob_thread.is_alive():
            with output_lock:
                echo("⚠ Warning: Some threads did not exit cleanly")
            return 1

    except KeyboardInterrupt:
        with output_lock:
            echo("\n\n⚠ Demo interrupted - cleaning up...")
        exit_event.set()
        alice_thread.join(timeout=Config.THREAD_TIMEOUT)
        bob_thread.join(timeout=Config.THREAD_TIMEOUT)
        return 130

    except Exception as e:
        with output_lock:
            echo(f"\n❌ Error running demo: {e}")
        return 1

    with output_lock:
        echo("\n╔════════════════════════════════════════════════════════════╗")
        echo("║  Demo Complete!                                            ║")
        echo("║                                                            ║")
        echo("║  You've seen:                                              ║")
        echo("║    ✓ getch() notification checking                         ║")
        echo("║    ✓ Thread-local member isolation                         ║")
        echo("║    ✓ Per-member notification queues                        ║")
        echo("║    ✓ Multi-user concurrent messaging                       ║")
        echo("║    ✓ Error handling for edge cases                         ║")
        echo("║                                                            ║")
        echo("║  See README_PING_PONG.md for more information              ║")
        echo("╚════════════════════════════════════════════════════════════╝\n")

    return 0


def main() -> int:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="BBSENGINE6 Ping-Pong Demo - Interactive messaging system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run default two-player demo (alice and bob)
  python -m bbsengine6.examples.ping_pong_demo

  # Run as alice in one terminal
  python -m bbsengine6.examples.ping_pong_demo --user alice

  # Run as bob in another terminal
  python -m bbsengine6.examples.ping_pong_demo --user bob

  # Run as custom player name
  python -m bbsengine6.examples.ping_pong_demo --user charlie
        """,
    )
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="Player name (use different names in separate terminals to play together)",
        metavar="NAME",
    )

    args = parser.parse_args()

    # If user specified, run single-player mode
    if args.user:
        # Validate moniker
        if not args.user or len(args.user) > 255:
            with output_lock:
                echo(f"❌ Invalid user name: {args.user}")
                echo("   User name must be 1-255 characters")
            return 1
        return run_single_player(args.user)
    else:
        # Default: run two-player mode
        return run_two_players()


if __name__ == "__main__":
    sys.exit(main())
