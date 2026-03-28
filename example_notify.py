#!/usr/bin/env python
"""
Simple standalone example of using the notification system.

This script demonstrates:
1. Sending notifications with templates
2. Receiving notifications
3. Using groups
4. Blocking users
5. Marking notifications as read

To run:
    cd /home/opencode/data/work/bbsengine6
    python example_notify.py
"""

from datetime import datetime, timezone

# Add py module to path
import sys

sys.path.insert(0, "py/src")

from bbsengine6.notify import (
    NotificationUrgency,
    send,
    get_notifications,
    mark_read,
    register_type,
    create_group,
    block,
    is_blocked,
)


def print_section(title):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def example_basic_send():
    """Example 1: Basic notification sending."""
    print_section("Example 1: Basic Notification Sending")

    # Register notification type
    print("1. Registering notification type...")
    register_type(
        type_name="EXAMPLE_BASIC",
        default_urgency=NotificationUrgency.ROUTINE,
        max_per_hour=100,
    )
    print("   ✓ Type registered\n")

    # Send notification
    print("2. Sending notification...")
    result = send(
        notification_type="EXAMPLE_BASIC",
        recipients=["jam"],
        template="Hello {name}, welcome to {system}!",
        template_vars={"name": "Jam", "system": "bbsengine6"},
        urgency=NotificationUrgency.ROUTINE,
    )
    print("   ✓ Notification sent")
    print(f"   - Message: {result.message}")
    print(f"   - Recipient: {result.recipients_ok}")
    print(f"   - ID: {result.id}\n")

    return result.id


def example_urgency_levels():
    """Example 2: Different urgency levels."""
    print_section("Example 2: Urgency Levels")

    register_type(
        type_name="EXAMPLE_URGENCY",
        default_urgency=NotificationUrgency.ROUTINE,
        max_per_hour=100,
    )

    # Send with different urgencies
    urgencies = [
        (NotificationUrgency.ROUTINE, "Regular update"),
        (NotificationUrgency.IMPORTANT, "Important announcement"),
        (NotificationUrgency.URGENT, "Urgent action needed"),
        (NotificationUrgency.CRITICAL, "CRITICAL: Immediate action"),
    ]

    for urgency, message in urgencies:
        result = send(
            notification_type="EXAMPLE_URGENCY",
            recipients=["jam"],
            template=message,
            urgency=urgency,
        )
        print(f"  {urgency.value:10} -> {result.message}")

    print()


def example_with_data():
    """Example 3: Notifications with structured data."""
    print_section("Example 3: Structured Data")

    register_type(
        type_name="EXAMPLE_DATA",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    print("Sending notification with structured data...\n")

    result = send(
        notification_type="EXAMPLE_DATA",
        recipients=["jam"],
        template="You earned {amount} {currency} in {game}!",
        template_vars={"amount": 1000, "currency": "credits", "game": "Blackjack"},
        urgency=NotificationUrgency.IMPORTANT,
        data={
            "game_type": "blackjack",
            "amount": 1000,
            "currency": "credits",
            "transaction_id": "txn_abc123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    print(f"  Message: {result.message}")
    print("  Structured data:")
    for key, value in result.data.items():
        print(f"    - {key}: {value}")
    print()


def example_groups():
    """Example 4: Group-based notifications."""
    print_section("Example 4: Group Targeting")

    register_type(
        type_name="EXAMPLE_GROUP",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    # Create group
    print("1. Creating group @guild:dragons with members...\n")
    create_group("@guild:dragons", member_monikers=["jam", "alice", "bob"])
    print("   ✓ Group created\n")

    # Send to group
    print("2. Sending notification to group...\n")
    result = send(
        notification_type="EXAMPLE_GROUP",
        recipients=["@guild:dragons"],
        template="Guild announcement: {msg}",
        template_vars={"msg": "Meeting in 10 minutes!"},
        urgency=NotificationUrgency.IMPORTANT,
    )

    print(f"   ✓ Sent to {len(result.recipients_ok)} guild members:")
    for member in result.recipients_ok:
        print(f"     - {member}")
    print()


def example_blocking():
    """Example 5: User blocking."""
    print_section("Example 5: User Blocking")

    print("1. jam blocks alice...\n")
    block("jam", "alice")
    print("   ✓ Blocked\n")

    print("2. Checking blocking status...\n")
    is_alice_blocked = is_blocked("alice", "jam")
    print(f"   - alice notifications to jam blocked: {is_alice_blocked}")
    is_bob_blocked = is_blocked("bob", "jam")
    print(f"   - bob notifications to jam blocked: {is_bob_blocked}\n")


def example_retrieve_notifications():
    """Example 6: Retrieving notifications."""
    print_section("Example 6: Retrieving Notifications")

    # Send some test notifications
    register_type(
        type_name="EXAMPLE_RETRIEVE",
        default_urgency=NotificationUrgency.ROUTINE,
        max_per_hour=100,
    )

    print("1. Sending test notifications...\n")
    for i in range(3):
        send(
            notification_type="EXAMPLE_RETRIEVE",
            recipients=["jam"],
            template=f"Test message {i + 1}",
            should_persist=True,
        )
    print("   ✓ Sent 3 notifications\n")

    # Retrieve all
    print("2. Retrieving all notifications...\n")
    all_notifs = get_notifications("jam", unread_only=False, limit=10)
    print(f"   Found {len(all_notifs)} notifications:")
    for notif in all_notifs[-3:]:  # Show last 3
        print(f"     - {notif.message[:50]}... (ID: {notif.id})")
    print()

    # Retrieve unread only
    print("3. Retrieving unread only...\n")
    unread = get_notifications("jam", unread_only=True, limit=10)
    print(f"   Found {len(unread)} unread notifications\n")

    # Mark one as read
    if all_notifs:
        print("4. Marking one as read...\n")
        mark_read(all_notifs[0].id, "jam")
        print(f"   ✓ Marked notification {all_notifs[0].id} as read\n")


def example_complete_workflow():
    """Example 7: Complete workflow."""
    print_section("Example 7: Complete Workflow")

    register_type(
        type_name="EXAMPLE_WORKFLOW",
        default_urgency=NotificationUrgency.IMPORTANT,
        max_per_hour=100,
    )

    # Step 1: Send
    print("Step 1: Sending notification...\n")
    result = send(
        notification_type="EXAMPLE_WORKFLOW",
        recipients=["jam"],
        sender_moniker="alice",
        template="{sender} shared: {title}",
        template_vars={"sender": "alice", "title": "Check this out!"},
        urgency=NotificationUrgency.IMPORTANT,
        data={"post_id": 12345, "shared_by": "alice"},
    )
    notify_id = result.id
    print(f"   ✓ Sent: {result.message}\n")

    # Step 2: Receive
    print("Step 2: Retrieving unread...\n")
    unread = get_notifications("jam", unread_only=True, limit=10)
    print(f"   ✓ Found {len(unread)} unread notifications\n")

    # Step 3: Read
    print("Step 3: Marking as read...\n")
    mark_read(notify_id, "jam")
    print("   ✓ Marked as read\n")

    # Step 4: Verify
    print("Step 4: Verifying status...\n")
    unread_after = get_notifications("jam", unread_only=True, limit=10)
    print(f"   ✓ Now {len(unread_after)} unread (was {len(unread)})\n")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("  bbsengine6 Notification System - Examples")
    print("=" * 60)

    try:
        example_basic_send()
        example_urgency_levels()
        example_with_data()
        example_groups()
        example_blocking()
        example_retrieve_notifications()
        example_complete_workflow()

        print("\n" + "=" * 60)
        print("  ✓ All examples completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Review the examples above")
        print("  2. Check NOTIFY_TESTING.md for more details")
        print("  3. Run: pytest tests/test_notify_integration.py -v -s")
        print("  4. Integrate into your application")
        print()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Make sure the database is running and initialized")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
