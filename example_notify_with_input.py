#!/usr/bin/env python
"""
Demonstration of notifications working during user input.

This script shows that the notification system works even when:
1. User is inside inputstring() waiting for text input
2. User is inside inputchoice() selecting from menu
3. Notifications arrive asynchronously in background
4. System continues responding to input while notifications queue up

To run:
    cd /home/opencode/data/work/bbsengine6
    python example_notify_with_input.py

This demonstrates the threading model where:
- Main thread: Blocked in input dialogs
- Background thread: Can receive/process notifications
- Queue: Notifications accumulate and are processed when available
"""

import sys
import threading
import time

sys.path.insert(0, "py/src")

from bbsengine6.notify import (
    NotificationUrgency,
    send,
    get_queue,
    register_type,
    create_group,
)
from bbsengine6.io import echo


def print_section(title):
    """Print a section header."""
    echo(f"\n{'=' * 70}")
    echo(f"  {title}")
    echo(f"{'=' * 70}\n")


def simulate_notifications_during_input():
    """Simulate receiving notifications while user is in input dialog."""
    print_section("Demo: Notifications During User Input")

    echo("This demo shows notifications arriving while user interacts.\n")

    # Register types
    register_type(
        type_name="DEMO_BACKGROUND",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    register_type(
        type_name="DEMO_URGENT",
        default_urgency=NotificationUrgency.URGENT,
        max_per_hour=100,
    )

    # Get queue for jam
    queue = get_queue("jam")
    echo("✓ Created notification queue for 'jam'\n")

    # Background thread that sends notifications
    def send_notifications_in_background():
        """Background thread sends notifications with delays."""
        time.sleep(2)
        echo("\n[BACKGROUND THREAD] Sending first notification...\n")
        send(
            notification_type="DEMO_BACKGROUND",
            recipients=["jam"],
            template="Message from {sender}: {msg}",
            template_vars={"sender": "alice", "msg": "Check this out!"},
            urgency=NotificationUrgency.IMPORTANT,
        )

        time.sleep(3)
        echo("\n[BACKGROUND THREAD] Sending second notification...\n")
        send(
            notification_type="DEMO_BACKGROUND",
            recipients=["jam"],
            template="Update: {msg}",
            template_vars={"msg": "Your task is ready"},
            urgency=NotificationUrgency.IMPORTANT,
        )

        time.sleep(2)
        echo("\n[BACKGROUND THREAD] Sending URGENT notification...\n")
        send(
            notification_type="DEMO_URGENT",
            recipients=["jam"],
            template="ALERT: {msg}",
            template_vars={"msg": "System maintenance in 5 minutes!"},
            urgency=NotificationUrgency.URGENT,
        )

    # Start background thread
    bg_thread = threading.Thread(target=send_notifications_in_background, daemon=True)
    bg_thread.start()

    echo("Background thread started (will send notifications in background)\n")
    echo("Simulating user input now...\n")
    echo("-" * 70)

    # Simulate user doing something for 10 seconds
    echo("Imagine user is here: inputstring('Enter your name: ')\n")
    echo("While waiting for input, notifications arrive in background...\n")

    for i in range(10):
        time.sleep(1)
        echo(f"  [Main] Second {i + 1}... user still typing...\n")

        # Check queue periodically
        if queue.size() > 0:
            echo(f"\n  ⚠️  {queue.size()} notification(s) in queue!\n")

    echo("-" * 70)
    echo("\nUser finished input.\n")

    # Show queued notifications
    echo("Checking notification queue...\n")
    queued = queue.get_all()
    echo(f"✓ Found {len(queued)} notifications that arrived during input:\n")

    for notif in queued:
        echo(f"  - [{notif.urgency.value}] {notif.message}")
        echo(f"    (ID: {notif.id}, Sender: {notif.sender_moniker})\n")


def demo_notifications_with_choice():
    """Demo notifications arriving while user is in inputchoice()."""
    print_section("Demo: Notifications During Menu Selection")

    echo("Scenario: User is selecting from menu while notifications arrive\n")

    register_type(
        type_name="DEMO_CHOICE",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    queue = get_queue("jam")

    # Background thread
    def send_during_choice():
        time.sleep(1)
        echo("\n[BACKGROUND] Sending notification...\n")
        send(
            notification_type="DEMO_CHOICE",
            recipients=["jam"],
            template="Friend {name} sent you a message",
            template_vars={"name": "bob"},
            urgency=NotificationUrgency.IMPORTANT,
        )

    bg_thread = threading.Thread(target=send_during_choice, daemon=True)
    bg_thread.start()

    echo("Simulating menu selection (inputchoice)...\n")
    echo("-" * 70)
    echo("Menu options:\n")
    echo("  1. Continue game")
    echo("  2. Check inventory")
    echo("  3. Settings")
    echo("\n(User is thinking about choice...)\n")

    for i in range(3):
        time.sleep(1)
        echo(f"  {i + 1} second(s) elapsed...\n")

    echo("-" * 70)
    echo(f"\nQueue size: {queue.size()} notification(s)\n")

    if queue.size() > 0:
        notif = queue.get_all()[0]
        echo(f"✓ Notification arrived: {notif.message}\n")


def demo_queue_during_work():
    """Demo notifications queuing up during ongoing work."""
    print_section("Demo: Queue Accumulation During Work")

    echo("Scenario: Multiple notifications arrive while user is busy\n")

    register_type(
        type_name="DEMO_WORK",
        default_urgency=NotificationUrgency.ROUTINE,
        max_per_hour=100,
    )

    # Create a group
    create_group("@team:dev", member_monikers=["jam", "alice", "bob"])

    queue = get_queue("jam")

    # Background: Multiple senders sending
    def send_many_notifications():
        senders = ["alice", "bob", "carol"]
        for i, sender in enumerate(senders):
            time.sleep(1.5)
            echo(f"\n[BACKGROUND] Sending from {sender}...\n")
            send(
                notification_type="DEMO_WORK",
                recipients=["jam"],
                template="{sender} sent: Task {num}",
                template_vars={"sender": sender, "num": i + 1},
                sender_moniker=sender,
                urgency=NotificationUrgency.ROUTINE,
            )

    bg_thread = threading.Thread(target=send_many_notifications, daemon=True)
    bg_thread.start()

    echo("Main thread simulating work for 6 seconds...\n")
    echo("-" * 70)

    for i in range(6):
        time.sleep(1)
        queue_size = queue.size()
        status = f"({queue_size} in queue)" if queue_size > 0 else ""
        echo(f"  [Main] Working... {status}\n")

    echo("-" * 70)

    echo("\nWork complete!\n")
    echo(f"Queue size: {queue.size()} notifications\n\n")

    # Process queue
    queued = queue.get_all()
    echo("Processing notifications:\n")
    for notif in queued:
        echo(f"  ✓ {notif.message}\n")


def demo_urgent_during_routine():
    """Demo urgent notification interrupting routine work."""
    print_section("Demo: Urgent Notification During Routine Work")

    echo("Scenario: User doing routine input, urgent alert arrives\n")

    register_type(
        type_name="DEMO_ROUTINE",
        default_urgency=NotificationUrgency.ROUTINE,
        max_per_hour=100,
    )

    register_type(
        type_name="DEMO_ALERT",
        default_urgency=NotificationUrgency.URGENT,
        max_per_hour=100,
    )

    queue = get_queue("jam")

    def send_urgent_alert():
        time.sleep(3)
        echo("\n[SYSTEM ALERT] URGENT notification incoming...\n")
        send(
            notification_type="DEMO_ALERT",
            recipients=["jam"],
            template="🚨 URGENT: {msg}",
            template_vars={"msg": "Your session expires in 2 minutes!"},
            urgency=NotificationUrgency.URGENT,
        )

    bg_thread = threading.Thread(target=send_urgent_alert, daemon=True)
    bg_thread.start()

    echo("User doing routine input...\n")
    echo("-" * 70)

    for i in range(5):
        time.sleep(1)
        echo(f"  [Main] Routine work... {i + 1}s\n")

        # Check for urgent
        if queue.has_urgent():
            echo("\n⚠️  URGENT notification detected!\n")
            echo("  Application should prioritize this!\n")

    echo("-" * 70)

    # Show all
    queued = queue.get_all()
    echo(f"\nTotal notifications: {len(queued)}\n")
    for notif in queued:
        echo(f"  [{notif.urgency.value}] {notif.message}\n")


def demo_queue_and_input_interaction():
    """Practical example: Check queue before and after input."""
    print_section("Demo: Practical Queue Handling")

    echo("Pattern: Check queue before input, process after input\n\n")

    register_type(
        type_name="DEMO_PATTERN",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    # Example code pattern
    echo("Recommended pattern:\n\n")

    code = """
# Before input
unread = get_notifications('jam', unread_only=True)
if unread:
    print(f"You have {len(unread)} unread notifications")

# User in input
response = inputstring('Enter name: ')

# After input - check queue
queue = get_queue('jam')
while queue.size() > 0:
    notif = queue.get_all()[0]
    print(f"Notification: {notif.message}")
    mark_read(notif.id, 'jam')
"""

    echo(code)
    echo("\nThis pattern ensures:\n")
    echo("  ✓ Database notifications loaded before input\n")
    echo("  ✓ Live queue processed after input completes\n")
    echo("  ✓ User sees all notifications in logical order\n")
    echo("  ✓ System remains responsive\n")


def main():
    """Run all demos."""
    echo("\n" + "=" * 70)
    echo("  bbsengine6 Notification System - Input Integration Demo")
    echo("=" * 70)

    try:
        # Demo 1: Notifications during string input
        simulate_notifications_during_input()

        # Demo 2: Notifications during menu choice
        demo_notifications_with_choice()

        # Demo 3: Queue accumulation
        demo_queue_during_work()

        # Demo 4: Urgent during routine
        demo_urgent_during_routine()

        # Demo 5: Pattern
        demo_queue_and_input_interaction()

        echo("\n" + "=" * 70)
        echo("  ✓ All demos completed!")
        echo("=" * 70)
        echo("\nKey Takeaways:\n")
        echo("  1. Notifications work in background while user inputs\n")
        echo("  2. Queue accumulates notifications asynchronously\n")
        echo("  3. Check queue.size() and queue.has_urgent() periodically\n")
        echo("  4. Process queue after input/blocking operations\n")
        echo("  5. Mark notifications read after displaying\n")
        echo("\nFor more examples:")
        echo("  - See: NOTIFY_TESTING.md")
        echo("  - Run: pytest tests/test_notify_integration.py -v -s")
        echo()

    except Exception as e:
        echo(f"\n❌ Error: {e}\n", level="error")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
