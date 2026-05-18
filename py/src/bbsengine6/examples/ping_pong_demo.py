#!/usr/bin/env python3
# ping_pong_demo.py
# Interactive ping/pong message exchange demo using getch() idle loop notification detection

import os
import sys
import threading
import time
from datetime import datetime
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from bbsengine6 import notify
    from bbsengine6.io import getch
    from bbsengine6.member import _threadlocal
    from bbsengine6.notify import NotificationUrgency
except ImportError as e:
    print(f"Error: Failed to import bbsengine6 modules: {e}")
    print("Make sure bbsengine6 is installed and in your Python path")
    sys.exit(1)

# Constants
MAX_ROUNDS = 5
GETCH_TIMEOUT = 2.0
DEMO_EXITING = False
PLAYERS = {"alice": None, "bob": None}


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

        print("✓ Notification types registered (in-memory)")
        return True
    except Exception as e:
        print(f"❌ Failed to register notifications: {e}")
        return False


def clear_screen() -> None:
    """Clear the terminal screen."""
    os.system("clear" if os.name == "posix" else "cls")


def display_menu(
    moniker: str, round_num: int, status: str, message_log: List[str]
) -> None:
    """Display the game menu and message log."""
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
    if message_log:
        for msg in message_log[-8:]:  # Show last 8 messages
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
    """Send a ping/pong notification with comprehensive error handling.

    This demo version uses the in-memory notification queue directly
    without requiring a database connection.
    """
    to_moniker = "bob" if from_moniker == "alice" else "alice"

    try:
        # Check if recipient queue exists (is logged in)
        try:
            recipient_queue = notify.get_queue(to_moniker)
            if recipient_queue is None:
                print(f"❌ ERROR: {to_moniker} is not logged in")
                input("Press Enter to continue...")
                return False
        except Exception as e:
            print(f"❌ ERROR: Cannot access {to_moniker}'s queue: {e}")
            input("Press Enter to continue...")
            return False

        # Determine message type and word
        msg_type = "pong_message" if from_moniker == "bob" else "ping_message"
        msg_word = "PONG" if from_moniker == "bob" else "PING"
        msg_text = f"{msg_word} #{round_num} from {from_moniker}"

        # Create a simple notification object for demo purposes
        try:
            from dataclasses import dataclass

            @dataclass
            class SimpleNotification:
                """Minimal notification for demo purposes."""

                message: str
                urgency: str
                timestamp: str
                notification_type: str
                sender_moniker: str

            notification = SimpleNotification(
                message=msg_text,
                urgency="ROUTINE",
                timestamp=datetime.now().isoformat(),
                notification_type=msg_type,
                sender_moniker=from_moniker,
            )

            # Add to recipient's queue directly
            recipient_queue.put(notification)

            print(f"✓ Sent {msg_word} #{round_num} to {to_moniker}")
            time.sleep(0.5)
            return True

        except Exception as e:
            error_str = str(e).lower()
            print(f"❌ ERROR: Failed to send: {e}")

            if "rate limit" in error_str:
                print("   → You've sent too many messages too quickly")
                print("   → Please wait a moment before sending again")
            elif "blocked" in error_str:
                print(f"   → {to_moniker} has blocked your messages")
            elif "not registered" in error_str:
                print(f"   → Notification type not registered")

            input("Press Enter to continue...")
            return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        input("Press Enter to continue...")
        return False


def check_and_display_queue(moniker: str, message_log: List[str]) -> None:
    """Check and display all pending notifications."""
    try:
        queue = notify.get_queue(moniker)
        if queue is None:
            print(f"❌ Queue not found for {moniker}")
            input("Press Enter to continue...")
            return

        all_notifs = queue.get_all()

        if not all_notifs:
            print(f"✓ No pending notifications for {moniker}")
            time.sleep(1)
            return

        print(f"\n─── Pending Notifications for {moniker} ───")
        for notif in all_notifs:
            try:
                msg = getattr(notif, "message", None) or "No message"
                urgency = getattr(notif, "urgency", None) or "ROUTINE"
                timestamp = getattr(notif, "timestamp", None) or "unknown"
                print(f"[{urgency:8}] {timestamp} | {msg}")
                message_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
            except AttributeError as e:
                print(f"⚠ Malformed notification: {e}")

        print("──────────────────────────────────────────")
        input("Press Enter to continue...")

    except Exception as e:
        print(f"❌ ERROR checking queue: {e}")
        input("Press Enter to continue...")


def player_loop(moniker: str) -> None:
    """Main game loop for a player (alice or bob)."""
    global DEMO_EXITING  # noqa: PLW0603
    # Set thread-local moniker (simulates logged-in member)
    _threadlocal.moniker = moniker

    round_num = 0
    message_log = []

    try:
        print(f"\n✓ {moniker.upper()} initialized (moniker={moniker})")
        time.sleep(1)

        while round_num < MAX_ROUNDS and not DEMO_EXITING:
            status = f"Waiting for input or notification... (Press F2 to check)"
            display_menu(moniker, round_num, status, message_log)

            try:
                # getch() automatically checks notifications and emits bell
                key = getch.getch_str(timeout=GETCH_TIMEOUT)

                # Handle no input (timeout)
                if key is None:
                    continue

                # Normalize key input
                key_lower = key.lower()

                # ESC - exit immediately (both players)
                if key == "\x1b":  # ESC character
                    DEMO_EXITING = True
                    print(f"\n✓ {moniker.upper()}: ESC pressed - exiting demo")
                    time.sleep(0.5)
                    break

                # Q - quit local player
                elif key_lower == "q":
                    print(f"\n✓ {moniker.upper()}: Quit")
                    time.sleep(0.5)
                    break

                # P - send ping/pong
                elif key_lower == "p":
                    if send_ping(moniker, round_num):
                        round_num += 1
                        msg_word = "PONG" if moniker == "bob" else "PING"
                        message_log.append(
                            f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Sent {msg_word} #{round_num}"
                        )

                # C - check and display notifications
                elif key_lower == "c":
                    check_and_display_queue(moniker, message_log)

                # F2 is handled by getch() internally - it shows notifications
                # but we also offer the 'C' command for explicit checking

            except KeyboardInterrupt:
                print(f"\n⚠ {moniker.upper()}: Interrupted")
                break
            except Exception as e:
                print(f"❌ {moniker.upper()}: Error processing input: {e}")
                time.sleep(0.5)
                continue

        # End of rounds
        if round_num >= MAX_ROUNDS and not DEMO_EXITING:
            print(f"\n✓ {moniker.upper()}: Completed {MAX_ROUNDS} rounds!")
            time.sleep(1)

    except Exception as e:
        print(f"❌ {moniker.upper()}: Unexpected error: {e}")
    finally:
        print(f"\n✓ {moniker.upper()}'s game ended")


def main() -> int:
    """Main entry point."""
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
        print("\nFailed to setup notifications. Exiting.")
        return 1

    print("\nStarting two concurrent player threads...")
    print("(Run this script in two separate terminals for full interactivity)")
    time.sleep(1)

    # Create threads for alice and bob
    alice_thread = threading.Thread(target=player_loop, args=("alice",), daemon=False)
    bob_thread = threading.Thread(target=player_loop, args=("bob",), daemon=False)

    try:
        alice_thread.start()
        bob_thread.start()

        # Wait for both threads to complete
        alice_thread.join()
        bob_thread.join()

    except KeyboardInterrupt:
        print("\n\n⚠ Demo interrupted by user")
        globals()["DEMO_EXITING"] = True  # Set global to stop all threads
        alice_thread.join(timeout=1.0)
        bob_thread.join(timeout=1.0)
        return 130

    except Exception as e:
        print(f"\n❌ Error running demo: {e}")
        return 1

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
