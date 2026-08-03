#!/usr/bin/env python
"""
Demonstration of the message system working during user input.

This script shows that the message system works even when:
1. User is inside inputstring() waiting for text input
2. User is inside inputchoice() selecting from menu
3. Messages arrive asynchronously in background
4. System continues responding to input while messages queue up

To run:
    cd /home/opencode/data/work/bbsengine6
    python example_message_with_input.py

This demonstrates the threading model where:
- Main thread: Blocked in input dialogs
- Background thread: Can send messages via store_message()
- Database: Messages persist immediately and are delivered on connect
"""

import sys
import threading
import time

sys.path.insert(0, "py/src")

from bbsengine6 import message
from bbsengine6.message import (
    MessageUrgency,
    create_message_group,
    get_unread_count,
    get_pending_messages_prioritized,
)
from bbsengine6.io import echo


def print_section(title: str) -> None:
    """Print a section header."""
    echo(f"\n{'=' * 70}")
    echo(f"  {title}")
    echo(f"{'=' * 70}\n")


def simulate_messages_during_input() -> None:
    """Simulate receiving messages while user is in input dialog."""
    print_section("Demo: Messages During User Input")

    echo("This demo shows messages arriving while user interacts.\n")

    # Background thread that sends messages with delays
    def send_messages_in_background() -> None:
        """Background thread sends messages with delays."""
        time.sleep(2)
        echo("\n[BACKGROUND THREAD] Sending first message...\n")
        message.store_message(
            channel="demo.background",
            sender_moniker="alice",
            content="Message from {sender}: {msg}",
            recipient_monikers=["jam"],
            template="Message from {sender}: {msg}",
            template_vars={"sender": "alice", "msg": "Check this out!"},
            urgency=MessageUrgency.IMPORTANT,
        )

        time.sleep(3)
        echo("\n[BACKGROUND THREAD] Sending second message...\n")
        message.store_message(
            channel="demo.background",
            sender_moniker="bob",
            content="Update: {msg}",
            recipient_monikers=["jam"],
            template="Update: {msg}",
            template_vars={"msg": "Your task is ready"},
            urgency=MessageUrgency.IMPORTANT,
        )

        time.sleep(2)
        echo("\n[BACKGROUND THREAD] Sending URGENT message...\n")
        message.store_message(
            channel="demo.urgent",
            sender_moniker="system",
            content="ALERT: {msg}",
            recipient_monikers=["jam"],
            template="ALERT: {msg}",
            template_vars={"msg": "System maintenance in 5 minutes!"},
            urgency=MessageUrgency.URGENT,
        )

    # Start background thread
    bg_thread = threading.Thread(target=send_messages_in_background, daemon=True)
    bg_thread.start()

    echo("Background thread started (will send messages in background)\n")
    echo("Simulating user input now...\n")
    echo("-" * 70)

    # Simulate user doing something for 10 seconds
    echo("Imagine user is here: inputstring('Enter your name: ')\n")
    echo("While waiting for input, messages arrive in background...\n")

    for i in range(10):
        time.sleep(1)
        unread = get_unread_count("jam")
        echo(f"  [Main] Second {i + 1}... user still typing... ({unread} unread)\n")

    echo("-" * 70)
    echo("\nUser finished input.\n")

    # Show queued messages
    echo("Checking pending messages...\n")
    queued = get_pending_messages_prioritized("jam", limit=10)
    queued = [m for m in queued if m["channel"].startswith("demo.")]
    echo(f"✓ Found {len(queued)} messages that arrived during input:\n")

    for m in queued:
        echo(f"  - [{m['urgency']:8}] {m['content']}")
        echo(f"    (ID: {m['id']}, Sender: {m['sender_moniker']})\n")


def demo_messages_with_choice() -> None:
    """Demo messages arriving while user is in inputchoice()."""
    print_section("Demo: Messages During Menu Selection")

    echo("Scenario: User is selecting from menu while messages arrive\n")

    # Background thread
    def send_during_choice() -> None:
        time.sleep(1)
        echo("\n[BACKGROUND] Sending message...\n")
        message.store_message(
            channel="demo.choice",
            sender_moniker="bob",
            content="Friend {name} sent you a message",
            recipient_monikers=["jam"],
            template="Friend {name} sent you a message",
            template_vars={"name": "bob"},
            urgency=MessageUrgency.IMPORTANT,
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
        echo(f"  {i + 1} second(s) elapsed... ({get_unread_count('jam')} unread)\n")

    echo("-" * 70)
    echo(f"\nUnread count: {get_unread_count('jam')} message(s)\n")

    pending = get_pending_messages_prioritized("jam", limit=10)
    choice_msgs = [m for m in pending if m["channel"] == "demo.choice"]
    if choice_msgs:
        echo(f"✓ Message arrived: {choice_msgs[0]['content']}\n")


def demo_queue_during_work() -> None:
    """Demo messages queuing up during ongoing work."""
    print_section("Demo: Queue Accumulation During Work")

    echo("Scenario: Multiple messages arrive while user is busy\n")

    # Create a group
    create_message_group(
        name="@team:dev",
        createdby="jam",
        description="Dev team",
    )

    # Background: Multiple senders sending
    def send_many_messages() -> None:
        senders = ["alice", "bob", "carol"]
        for i, sender in enumerate(senders):
            time.sleep(1.5)
            echo(f"\n[BACKGROUND] Sending from {sender}...\n")
            message.store_message(
                channel="demo.work",
                sender_moniker=sender,
                content="{sender} sent: Task {num}",
                recipient_monikers=["jam"],
                template="{sender} sent: Task {num}",
                template_vars={"sender": sender, "num": i + 1},
                urgency=MessageUrgency.ROUTINE,
            )

    bg_thread = threading.Thread(target=send_many_messages, daemon=True)
    bg_thread.start()

    echo("Main thread simulating work for 6 seconds...\n")
    echo("-" * 70)

    for i in range(6):
        time.sleep(1)
        unread = get_unread_count("jam")
        status = f"({unread} unread)" if unread > 0 else ""
        echo(f"  [Main] Working... {status}\n")

    echo("-" * 70)

    echo("\nWork complete!\n")
    echo(f"Unread count: {get_unread_count('jam')} messages\n\n")

    # Process queue
    pending = get_pending_messages_prioritized("jam", limit=10)
    work_msgs = [m for m in pending if m["channel"] == "demo.work"]
    echo("Processing messages:\n")
    for m in work_msgs:
        echo(f"  ✓ {m['content']}\n")


def demo_urgent_during_routine() -> None:
    """Demo urgent message interrupting routine work."""
    print_section("Demo: Urgent Message During Routine Work")

    echo("Scenario: User doing routine input, urgent alert arrives\n")

    def send_urgent_alert() -> None:
        time.sleep(3)
        echo("\n[SYSTEM ALERT] URGENT message incoming...\n")
        message.store_message(
            channel="demo.alert",
            sender_moniker="system",
            content="🚨 URGENT: {msg}",
            recipient_monikers=["jam"],
            template="🚨 URGENT: {msg}",
            template_vars={"msg": "Your session expires in 2 minutes!"},
            urgency=MessageUrgency.URGENT,
        )

    bg_thread = threading.Thread(target=send_urgent_alert, daemon=True)
    bg_thread.start()

    echo("User doing routine input...\n")
    echo("-" * 70)

    for i in range(5):
        time.sleep(1)
        echo(f"  [Main] Routine work... {i + 1}s ({get_unread_count('jam')} unread)\n")

    echo("-" * 70)

    # Show all
    pending = get_pending_messages_prioritized("jam", limit=10)
    relevant = [m for m in pending if m["channel"].startswith("demo.")]
    echo(f"\nTotal demo messages: {len(relevant)}\n")
    for m in relevant:
        echo(f"  [{m['urgency']:8}] {m['content']}\n")

    if any(m["urgency"] in ("URGENT", "CRITICAL") for m in relevant):
        echo("\n⚠️  URGENT message detected!\n")
        echo("  Application should prioritize this!\n")


def demo_queue_and_input_interaction() -> None:
    """Practical example: Check queue before and after input."""
    print_section("Demo: Practical Queue Handling")

    echo("Pattern: Check queue before input, process after input\n\n")

    # Example code pattern
    echo("Recommended pattern:\n\n")

    code = """
# Before input
unread = get_unread_count('jam')
if unread:
    print(f"You have {unread} unread messages")

# User in input
response = inputstring('Enter name: ')

# After input - process pending messages (prioritized)
pending = get_pending_messages_prioritized('jam', limit=50)
for msg in pending:
    print(f"[{msg['urgency']}] {msg['content']}")
    mark_read(msg['id'], 'jam')
"""

    echo(code)
    echo("\nThis pattern ensures:\n")
    echo("  ✓ Unread count visible before input\n")
    echo("  ✓ Pending messages processed in urgency order\n")
    echo("  ✓ User sees critical/urgent messages first\n")
    echo("  ✓ System remains responsive\n")


def main() -> None:
    """Run all demos."""
    echo("\n" + "=" * 70)
    echo("  bbsengine6 Message System - Input Integration Demo")
    echo("=" * 70)

    try:
        simulate_messages_during_input()
        demo_messages_with_choice()
        demo_queue_during_work()
        demo_urgent_during_routine()
        demo_queue_and_input_interaction()

        echo("\n" + "=" * 70)
        echo("  ✓ All demos completed!")
        echo("=" * 70)
        echo("\nKey Takeaways:\n")
        echo("  1. Messages are stored immediately and persist across input\n")
        echo("  2. get_unread_count() is a fast cache lookup for bottombar\n")
        echo("  3. get_pending_messages_prioritized() surfaces urgent first\n")
        echo("  4. Check unread counts during long input operations\n")
        echo("  5. Mark messages read after displaying\n")
        echo("\nFor more examples:")
        echo("  - See: example_message.py")
        echo("  - Run: pytest tests/test_message_lib.py -v")
        echo()

    except Exception as e:
        echo(f"\n❌ Error: {e}\n", level="error")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
