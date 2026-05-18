#!/usr/bin/env python3
# ping_pong_demo.py
# Interactive ping/pong message exchange demo using getch() idle loop notification detection
# Thread-safe implementation with proper synchronization and graceful shutdown

import atexit
import os
import signal
import sys
import threading
import time
from collections import deque
from datetime import datetime
from typing import Deque, List, Union

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bbsengine6 import notify
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
            print("✓ Notification types registered (in-memory)")
        return True
    except Exception as e:
        with output_lock:
            print(f"❌ Failed to register notifications: {e}")
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
        print("═" * 60)
        print(f"    PING-PONG DEMO (Moniker: {moniker.upper()})")
        print("═" * 60)
        print(f"Round: {round_num}/{MAX_ROUNDS} | Status: {status}")
        print()
        print("(P)ing / (C)heck / (Q)uit / [ESC] to exit")
        print()
        print("─" * 60)
        print("MESSAGE LOG:")

        with message_log_lock:
            if message_log:
                # Show last 8 messages (works with both list and deque)
                log_items = list(message_log)[-8:]
                for msg in log_items:
                    print(f"  {msg}")
            else:
                print("  [Awaiting first message...]")

        print("─" * 60)

        # Show queue status
        try:
            queue = notify.get_queue(moniker)
            if queue:
                all_notifs = queue.get_all()
                count = len(all_notifs)
                print(f"Queue Status: {count} pending notification(s)")
            else:
                print("Queue Status: Not initialized")
        except Exception as e:
            print(f"Queue Status: Error - {e}")

        print("═" * 60)


def send_ping(from_moniker: str, round_num: int) -> bool:
    """Send a ping/pong notification with comprehensive error handling."""
    to_moniker = "bob" if from_moniker == "alice" else "alice"

    try:
        # Determine message type and word
        msg_type = "pong_message" if from_moniker == "bob" else "ping_message"
        msg_word = "PONG" if from_moniker == "bob" else "PING"
        msg_text = f"{msg_word} #{round_num + 1} from {from_moniker}"

        # Create a proper Notification object for the demo
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

        # Try to add to recipient's queue (atomic operation)
        # This approach avoids race condition of check-then-use
        try:
            recipient_queue = notify.get_queue(to_moniker)
            if recipient_queue is None:
                raise RuntimeError(f"{to_moniker} is not logged in")
            recipient_queue.put(notification)

            with output_lock:
                print(f"✓ Sent {msg_word} #{round_num + 1} to {to_moniker}")
            time.sleep(0.5)
            return True

        except (RuntimeError, AttributeError, TypeError) as e:
            error_str = str(e).lower()
            with output_lock:
                print(f"❌ ERROR: Failed to send to {to_moniker}: {e}")

                if "not logged in" in error_str:
                    print(f"   → {to_moniker} is not currently available")
                elif "rate limit" in error_str:
                    print("   → You've sent too many messages too quickly")
                    print("   → Please wait a moment before sending again")
                elif "blocked" in error_str:
                    print(f"   → {to_moniker} has blocked your messages")
                elif "not registered" in error_str:
                    print(f"   → Notification type not registered")

                input("Press Enter to continue...")
            return False

    except Exception as e:
        with output_lock:
            print(f"❌ Unexpected error: {e}")
            input("Press Enter to continue...")
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
                print(f"❌ Queue not found for {moniker}")
                input("Press Enter to continue...")
            return

        all_notifs = queue.get_all()

        if not all_notifs:
            with output_lock:
                print(f"✓ No pending notifications for {moniker}")
            time.sleep(1)
            return

        with output_lock:
            print(f"\n─── Pending Notifications for {moniker} ───")
            for notif in all_notifs:
                try:
                    msg = getattr(notif, "message", None) or "No message"
                    urgency = getattr(notif, "urgency", None) or "ROUTINE"
                    timestamp = getattr(notif, "timestamp", None) or "unknown"
                    print(f"[{urgency:8}] {timestamp} | {msg}")

                    with message_log_lock:
                        message_log.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
                        )
                except AttributeError as e:
                    print(f"⚠ Malformed notification: {e}")

            print("──────────────────────────────────────────")
            input("Press Enter to continue...")

    except Exception as e:
        with output_lock:
            print(f"❌ ERROR checking queue: {e}")
            input("Press Enter to continue...")


def player_loop(moniker: str) -> None:
    """Main game loop for a player (alice or bob) - fully thread-safe."""
    # Set thread-local moniker (simulates logged-in member)
    _threadlocal.moniker = moniker

    # Use deque with max size for automatic log rotation
    message_log = deque(maxlen=Config.MESSAGE_LOG_SIZE)

    try:
        with output_lock:
            print(f"\n✓ {moniker.upper()} initialized (moniker={moniker})")
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
                        print(f"\n✓ {moniker.upper()}: ESC pressed - exiting demo")
                    time.sleep(0.5)
                    break

                # Q - quit local player
                elif key_upper == "Q":
                    with output_lock:
                        print(f"\n✓ {moniker.upper()}: Quit")
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
                    print(f"\n⚠ {moniker.upper()}: Interrupted")
                exit_event.set()
                break
            except Exception as e:
                with output_lock:
                    print(f"❌ {moniker.upper()}: Error processing input: {e}")
                time.sleep(0.5)
                continue

        # End of rounds
        with round_counter_lock:
            final_round = shared_rounds[moniker]
        if final_round >= MAX_ROUNDS and not exit_event.is_set():
            with output_lock:
                print(f"\n✓ {moniker.upper()}: Completed {MAX_ROUNDS} rounds!")
            time.sleep(1)

    except Exception as e:
        with output_lock:
            print(f"❌ {moniker.upper()}: Unexpected error: {e}")
    finally:
        with output_lock:
            print(f"\n✓ {moniker.upper()}'s game ended")


def signal_handler(signum: int, frame) -> None:
    """Handle SIGINT (CTRL+C) gracefully."""
    with output_lock:
        print("\n\n⚠ Received interrupt signal - initiating graceful shutdown...")
    exit_event.set()


def cleanup_threads() -> None:
    """Cleanup function called on exit."""
    with output_lock:
        print("\n✓ Cleanup: Waiting for threads to finish...")

    # Set exit event in case it wasn't already set
    exit_event.set()

    # Wait for all active threads
    with active_threads_lock:
        for thread in active_threads:
            if thread.is_alive():
                with output_lock:
                    print(f"✓ Cleanup: Waiting for {thread.name}... (max {Config.THREAD_TIMEOUT}s)")
                thread.join(timeout=Config.THREAD_TIMEOUT)
                if thread.is_alive():
                    with output_lock:
                        print(f"⚠ Cleanup: {thread.name} did not exit cleanly")


def main() -> int:
    """Main entry point."""
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Register cleanup function to run on exit
    atexit.register(cleanup_threads)

    with output_lock:
        print("\n╔════════════════════════════════════════════════════════════╗")
        print("║  BBSENGINE6 PING-PONG DEMO                                 ║")
        print("║  Demonstrates getch() idle loop notification detection      ║")
        print("║  with multi-member per-machine support                      ║")
        print("╚════════════════════════════════════════════════════════════╝\n")

        print("This demo shows:")
        print("  • Two concurrent players (alice and bob) on same machine")
        print("  • Thread-local moniker isolation for per-member queues")
        print("  • getch() integration for automatic notification detection")
        print("  • Bell emission when notifications arrive")
        print("  • Comprehensive error handling for failure scenarios")
        print("\nFor full documentation, see: README_PING_PONG.md\n")

        input("Press Enter to start...")

    # Setup notification types
    if not setup_notifications():
        with output_lock:
            print("\nFailed to setup notifications. Exiting.")
        return 1

    with output_lock:
        print("\nStarting two concurrent player threads...")
        print("(Run this script in two separate terminals for full interactivity)")
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
            print(f"✓ Waiting for player threads (max {Config.THREAD_TIMEOUT}s)...")

        alice_thread.join(timeout=Config.THREAD_TIMEOUT)
        bob_thread.join(timeout=Config.THREAD_TIMEOUT)

        # Check if threads are still alive
        if alice_thread.is_alive() or bob_thread.is_alive():
            with output_lock:
                print("⚠ Warning: Some threads did not exit cleanly")
            return 1

    except KeyboardInterrupt:
        with output_lock:
            print("\n\n⚠ Demo interrupted - cleaning up...")
        exit_event.set()
        alice_thread.join(timeout=Config.THREAD_TIMEOUT)
        bob_thread.join(timeout=Config.THREAD_TIMEOUT)
        return 130

    except Exception as e:
        with output_lock:
            print(f"\n❌ Error running demo: {e}")
        return 1

    with output_lock:
        print("\n╔════════════════════════════════════════════════════════════╗")
        print("║  Demo Complete!                                            ║")
        print("║                                                            ║")
        print("║  You've seen:                                              ║")
        print("║    ✓ getch() notification checking                         ║")
        print("║    ✓ Thread-local member isolation                         ║")
        print("║    ✓ Per-member notification queues                        ║")
        print("║    ✓ Multi-user concurrent messaging                       ║")
        print("║    ✓ Error handling for edge cases                         ║")
        print("║                                                            ║")
        print("║  See README_PING_PONG.md for more information              ║")
        print("╚════════════════════════════════════════════════════════════╝\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
