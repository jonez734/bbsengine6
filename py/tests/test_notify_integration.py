"""
Integration tests for bbsengine6.notify - Send and receive notifications.

This module provides practical examples of:
1. Registering notification types
2. Sending notifications to users and groups
3. Receiving and querying notifications
4. Handling blocking and rate limiting
5. Managing notification groups

Note: These tests require a database connection and will use the postgres database.
Run with: pytest tests/test_notify_integration.py -v -s
"""

import pytest
from datetime import datetime, timezone

from bbsengine6.notify import (
    NotificationUrgency,
    send,
    get_notifications,
    get_queue,
    get_urgent,
    mark_read,
    register_type,
    get_types,
    create_group,
    add_to_group,
    get_group_members,
    block,
    unblock,
    is_blocked,
    get_blocked,
)


class TestNotificationSendAndReceive:
    """Practical examples of sending and receiving notifications."""

    def test_send_simple_notification(self):
        """Example: Send a simple notification to a user."""
        # Register the type first
        register_type(
            type_name="TEST_SIMPLE",
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        # Send a notification
        result = send(
            notification_type="TEST_SIMPLE",
            recipients=["jam"],
            template="Hello {name}, this is a test notification",
            template_vars={"name": "Jam"},
        )

        # Verify send result
        assert result.notification_type == "TEST_SIMPLE"
        assert result.message == "Hello Jam, this is a test notification"
        assert "jam" in result.recipients_ok
        assert len(result.recipients_failed) == 0
        assert result.urgency == NotificationUrgency.ROUTINE
        print(f"✓ Sent notification with ID {result.id}")

    def test_send_with_urgency(self):
        """Example: Send notifications with different urgency levels."""
        register_type(
            type_name="TEST_URGENCY",
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        # ROUTINE notification
        routine = send(
            notification_type="TEST_URGENCY",
            recipients=["jam"],
            template="This is routine",
            urgency=NotificationUrgency.ROUTINE,
        )
        assert routine.urgency == NotificationUrgency.ROUTINE

        # URGENT notification
        urgent = send(
            notification_type="TEST_URGENCY",
            recipients=["jam"],
            template="This is urgent!",
            urgency=NotificationUrgency.URGENT,
        )
        assert urgent.urgency == NotificationUrgency.URGENT

        # CRITICAL notification
        critical = send(
            notification_type="TEST_URGENCY",
            recipients=["jam"],
            template="CRITICAL: System alert",
            urgency=NotificationUrgency.CRITICAL,
        )
        assert critical.urgency == NotificationUrgency.CRITICAL

        print("✓ Sent 3 notifications with different urgencies")

    def test_send_with_data(self):
        """Example: Send notification with structured data for programmatic use."""
        register_type(
            type_name="TEST_DATA",
            default_urgency=NotificationUrgency.IMPORTANT,
            max_per_hour=100,
        )

        result = send(
            notification_type="TEST_DATA",
            recipients=["jam"],
            template="You won {amount} credits in {game}!",
            template_vars={"amount": 1000, "game": "Blackjack"},
            data={
                "game_type": "blackjack",
                "amount": 1000,
                "transaction_id": "txn_12345",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        assert result.data["game_type"] == "blackjack"
        assert result.data["amount"] == 1000
        print("✓ Sent notification with structured data")

    def test_send_to_multiple_recipients(self):
        """Example: Send same notification to multiple users."""
        register_type(
            type_name="TEST_MULTIPLE",
            default_urgency=NotificationUrgency.IMPORTANT,
            max_per_hour=100,
        )

        result = send(
            notification_type="TEST_MULTIPLE",
            recipients=["jam", "alice", "bob"],
            template="Tournament event: {event}",
            template_vars={"event": "Joust Battle Royale"},
            urgency=NotificationUrgency.IMPORTANT,
        )

        # Check which users actually received it
        print(f"✓ Attempted to send to: {result.recipients}")
        print(f"  - Successfully received by: {result.recipients_ok}")
        print(f"  - Failed to send to: {result.recipients_failed}")
        if result.errors:
            print(f"  - Errors: {result.errors}")


class TestNotificationGroups:
    """Examples of group-based notification targeting."""

    def test_create_and_use_group(self):
        """Example: Create a group and send notification to group members."""
        # Create a group
        create_group(
            group_name="@guild:dragons", member_monikers=["jam", "alice", "bob"]
        )

        # Verify members
        members = get_group_members("@guild:dragons")
        print(f"✓ Created group @guild:dragons with members: {members}")
        assert "jam" in members

        # Register notification type
        register_type(
            type_name="GUILD_ANNOUNCEMENT",
            default_urgency=NotificationUrgency.IMPORTANT,
            max_per_hour=100,
        )

        # Send to group
        result = send(
            notification_type="GUILD_ANNOUNCEMENT",
            recipients=["@guild:dragons"],
            template="Guild meeting in {minutes} minutes!",
            template_vars={"minutes": 5},
            urgency=NotificationUrgency.IMPORTANT,
        )

        print(f"✓ Sent notification to {len(result.recipients_ok)} guild members")
        assert len(result.recipients_ok) > 0

    def test_add_remove_group_members(self):
        """Example: Dynamically manage group membership."""
        # Create empty group
        create_group(group_name="@faction:empire")

        # Add members
        add_to_group("@faction:empire", "jam")
        add_to_group("@faction:empire", "alice")

        members = get_group_members("@faction:empire")
        print(f"✓ Group @faction:empire members: {members}")
        assert len(members) == 2

        # This would remove a member (if implemented):
        # remove_from_group("@faction:empire", "alice")


class TestNotificationBlocking:
    """Examples of blocking and unblocking notifications."""

    def test_block_sender(self):
        """Example: User blocks notifications from another user."""
        # jam blocks alice
        block("jam", "alice")

        # Verify blocking
        is_jam_blocked_alice = is_blocked("alice", "jam")
        print(f"✓ alice -> jam blocked: {is_jam_blocked_alice}")
        assert is_jam_blocked_alice is True

        # alice cannot block jam (separate relationship)
        is_alice_blocked_jam = is_blocked("jam", "alice")
        print(f"  jam -> alice blocked: {is_alice_blocked_jam}")

        # Get all users who blocked jam
        blocked_jam = get_blocked("jam")
        print(f"  Users who blocked jam: {blocked_jam}")

    def test_unblock_sender(self):
        """Example: User unblocks a previously blocked sender."""
        # Block first
        block("jam", "alice")

        # Verify blocked
        assert is_blocked("alice", "jam") is True

        # Unblock
        unblock("jam", "alice")

        # Verify unblocked
        assert is_blocked("alice", "jam") is False
        print("✓ Unblocked alice from jam")


class TestNotificationRetrieval:
    """Examples of retrieving and consuming notifications."""

    def test_get_notifications_from_db(self):
        """Example: Retrieve user's notifications from database."""
        register_type(
            type_name="TEST_RETRIEVAL",
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        # Send a notification
        send(
            notification_type="TEST_RETRIEVAL",
            recipients=["jam"],
            template="Test message 1",
            should_persist=True,
        )

        # Retrieve notifications
        notifications = get_notifications("jam", unread_only=False, limit=10)

        print(f"✓ Retrieved {len(notifications)} notifications for jam")
        if notifications:
            latest = notifications[0]
            print(f"  Latest: {latest.message}")
            print(f"  Type: {latest.notification_type}")
            print(f"  Urgency: {latest.urgency.value}")

    def test_get_unread_notifications(self):
        """Example: Retrieve only unread notifications."""
        register_type(
            type_name="TEST_UNREAD",
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        # Send notification
        result = send(
            notification_type="TEST_UNREAD",
            recipients=["jam"],
            template="Unread message",
            should_persist=True,
        )
        notify_id = result.id

        # Get unread notifications
        unread = get_notifications("jam", unread_only=True, limit=10)
        print(f"✓ Retrieved {len(unread)} unread notifications for jam")

        # Mark as read
        mark_read(notify_id, "jam")
        print(f"  Marked notification {notify_id} as read")

        # Get unread again (should have fewer)
        unread_after = get_notifications("jam", unread_only=True, limit=10)
        print(f"  Unread after marking: {len(unread_after)}")

    def test_get_urgent_notifications(self):
        """Example: Retrieve only urgent/critical notifications."""
        register_type(
            type_name="TEST_GET_URGENT",
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        # Send mix of urgencies
        send(
            notification_type="TEST_GET_URGENT",
            recipients=["jam"],
            template="Routine message",
            urgency=NotificationUrgency.ROUTINE,
            should_persist=True,
        )

        send(
            notification_type="TEST_GET_URGENT",
            recipients=["jam"],
            template="URGENT message",
            urgency=NotificationUrgency.URGENT,
            should_persist=True,
        )

        # Get urgent only
        urgent = get_urgent("jam")
        print(f"✓ Retrieved {len(urgent)} urgent/critical notifications")
        for u in urgent:
            print(f"  - {u.urgency.value}: {u.message}")


class TestNotificationQueue:
    """Examples of using live notification queues."""

    def test_notification_queue_basic(self):
        """Example: Use in-memory queue for real-time notifications."""
        # Get queue for a user
        queue = get_queue("jam")

        # Queue starts empty
        assert queue.size() == 0
        print(f"✓ Queue for jam created (size: {queue.size()})")

        # In a real application:
        # - Application code puts notifications in the queue
        # - UI/client code gets notifications with queue.get(timeout=5.0)
        # - Example:
        #   notification = queue.get(timeout=5.0)
        #   if notification:
        #       show_popup(notification.message)
        #       mark_read(notification.id, "jam")

    def test_queue_urgent_check(self):
        """Example: Check if queue has urgent notifications."""
        queue = get_queue("alice")

        # Queue starts empty, no urgent
        assert not queue.has_urgent()
        print(f"✓ Queue has_urgent: {queue.has_urgent()}")

        # In production, send() would add to queue if user is online
        # Then check:
        #   if queue.has_urgent():
        #       play_alert_sound()


class TestNotificationTypes:
    """Examples of managing notification types."""

    def test_register_type_with_settings(self):
        """Example: Register notification type with custom settings."""
        register_type(
            type_name="GAME_EVENT",
            default_urgency=NotificationUrgency.URGENT,
            max_per_hour=50,
            persist_by_default=True,
        )

        print("✓ Registered type GAME_EVENT")

    def test_get_all_types(self):
        """Example: List all registered notification types."""
        # Register a few types
        register_type("TYPE_A", NotificationUrgency.ROUTINE, 10)
        register_type("TYPE_B", NotificationUrgency.URGENT, 50)

        # Get all types
        types = get_types()

        print(f"✓ Retrieved {len(types)} notification types:")
        for type_name, settings in list(types.items())[:5]:
            print(
                f"  - {type_name}: {settings['default_urgency']} ({settings['max_per_hour']}/hr)"
            )


class TestRateLimiting:
    """Examples of rate limiting behavior."""

    def test_rate_limit_concept(self):
        """Example: Understanding rate limiting."""
        register_type(
            type_name="LIMITED_EVENT",
            max_per_hour=3,  # Max 3 per hour
            default_urgency=NotificationUrgency.ROUTINE,
        )

        print("✓ Registered type LIMITED_EVENT with max_per_hour=3")

        # In production, attempting to send more than 3 in one hour would
        # raise RuntimeError: "Rate limit exceeded for LIMITED_EVENT"

        # Rate limits are stored in database __notify_rate_limit table
        # so website can query remaining capacity:
        # SELECT
        #     nt.type_name,
        #     nrl.send_count,
        #     nt.max_per_user_per_hour,
        #     (nt.max_per_user_per_hour - nrl.send_count) as remaining
        # FROM engine.__notify_rate_limit nrl
        # JOIN engine.__notify_type nt ON nrl.notification_type = nt.type_name
        # WHERE nrl.sender_moniker = 'jam'
        #   AND (now() - nrl.window_start) < interval '1 hour'


class TestCompleteWorkflow:
    """End-to-end workflow examples."""

    def test_complete_notification_workflow(self):
        """Example: Complete workflow from sending to receiving to reading."""

        # Step 1: Register notification type
        register_type(
            type_name="WORKFLOW_TEST",
            default_urgency=NotificationUrgency.IMPORTANT,
            max_per_hour=100,
        )
        print("Step 1: ✓ Registered WORKFLOW_TEST type")

        # Step 2: Create a group
        create_group("@test:group", member_monikers=["jam", "alice"])
        print("Step 2: ✓ Created @test:group with jam and alice")

        # Step 3: Send notification to group
        result = send(
            notification_type="WORKFLOW_TEST",
            recipients=["@test:group"],
            template="{sender} sent you a message: {msg}",
            template_vars={"sender": "alice", "msg": "Hello from the group!"},
            sender_moniker="alice",
            data={"group": "test:group"},
        )
        print(
            f"Step 3: ✓ Sent notification to {len(result.recipients_ok)} group members"
        )
        notify_id = result.id

        # Step 4: Retrieve notification
        notifications = get_notifications("jam", unread_only=True)
        print(f"Step 4: ✓ Retrieved {len(notifications)} unread for jam")

        # Step 5: Mark as read
        mark_read(notify_id, "jam")
        print(f"Step 5: ✓ Marked notification {notify_id} as read")

        # Step 6: Verify it's no longer unread
        unread = get_notifications("jam", unread_only=True)
        print(f"Step 6: ✓ Now {len(unread)} unread (should be fewer)")

    def test_social_notification_example(self):
        """Example: Real-world social feature notification."""
        register_type(
            type_name="POST_SHARED",
            default_urgency=NotificationUrgency.IMPORTANT,
            max_per_hour=100,
        )

        # Alice shares a post with jam
        result = send(
            notification_type="POST_SHARED",
            recipients=["jam"],
            sender_moniker="alice",
            template='{sender} shared a post: "{title}"',
            template_vars={"sender": "alice", "title": "Check this amazing discovery!"},
            urgency=NotificationUrgency.IMPORTANT,
            data={
                "post_id": 12345,
                "shared_by": "alice",
                "shared_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"✓ Social notification sent: {result.message}")
        print(f"  Post ID: {result.data['post_id']}")

    def test_game_victory_example(self):
        """Example: Game victory notification."""
        register_type(
            type_name="GAME_VICTORY",
            default_urgency=NotificationUrgency.URGENT,
            max_per_hour=50,
        )

        result = send(
            notification_type="GAME_VICTORY",
            recipients=["jam"],
            template="Victory! You defeated {opponent}! Earned {credits} credits.",
            template_vars={"opponent": "barbarians", "credits": 500},
            urgency=NotificationUrgency.URGENT,
            data={
                "game": "empyre",
                "opponent_id": "barbarians",
                "reward": 500,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        print(f"✓ Game victory notification: {result.message}")
        print(f"  Reward: {result.data['reward']} credits")


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_notify_integration.py -v -s
    pytest.main([__file__, "-v", "-s"])
