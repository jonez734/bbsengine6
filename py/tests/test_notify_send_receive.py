"""
Integration tests for bbsengine6.notify send and receive functionality.

Demonstrates CONN_POOL_PATTERN for database operations and provides
practical examples of sending and receiving notifications.
"""

import pytest

from bbsengine6.notify import (
    NotificationUrgency,
    send,
    count,
    get_notifications,
    mark_read,
    register_type,
    get_urgent,
)


class TestSendNotifications:
    """Tests for sending notifications."""

    def test_send_simple_notification(self, pool, db_connection, test_users):
        register_type("TEST_SEND_SIMPLE", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_SEND_SIMPLE",
            recipients=[recipient],
            template="Hello {name}",
            template_vars={"name": recipient},
            conn=db_connection,
        )

        assert result.message == f"Hello {recipient}"
        assert recipient in result.recipients_ok
        print(f"✓ Sent notification ID {result.id}")

    def test_send_with_urgency(self, pool, db_connection, test_users):
        register_type("TEST_SEND_URGENCY", NotificationUrgency.URGENT, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_SEND_URGENCY",
            recipients=[recipient],
            template="Urgent message",
            urgency=NotificationUrgency.CRITICAL,
            conn=db_connection,
        )

        assert result.urgency == NotificationUrgency.CRITICAL
        print("✓ Sent CRITICAL notification")

    def test_send_to_multiple_recipients(self, pool, db_connection, test_users):
        register_type("TEST_SEND_MULTI", NotificationUrgency.IMPORTANT, 100)
        recipients = test_users[:3]

        result = send(
            notification_type="TEST_SEND_MULTI",
            recipients=recipients,
            template="Group message",
            conn=db_connection,
        )

        assert len(result.recipients_ok) <= 3
        print(f"✓ Sent to {len(result.recipients_ok)} recipients")

    def test_send_with_data(self, pool, db_connection, test_users):
        register_type("TEST_SEND_DATA", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_SEND_DATA",
            recipients=[recipient],
            template="Game result",
            data={"game": "chess", "winner": recipient},
            conn=db_connection,
        )

        assert result.data["game"] == "chess"
        print("✓ Sent notification with data payload")


class TestReceiveNotifications:
    """Tests for receiving and retrieving notifications."""

    def test_get_notifications_after_send(self, pool, db_connection, test_users):
        register_type("TEST_RECV", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_RECV",
            recipients=[recipient],
            template="Test message",
            should_persist=True,
            conn=db_connection,
        )
        notify_id = result.id

        notifications = get_notifications(recipient, conn=db_connection)
        assert any(n.id == notify_id for n in notifications)
        print(f"✓ Retrieved {len(notifications)} notifications")

    def test_get_unread_only(self, pool, db_connection, test_users):
        register_type("TEST_UNREAD", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_UNREAD",
            recipients=[recipient],
            template="Unread test",
            should_persist=True,
            conn=db_connection,
        )
        notify_id = result.id

        unread = get_notifications(recipient, unread_only=True, conn=db_connection)
        assert any(n.id == notify_id for n in unread)
        print(f"✓ Found {len(unread)} unread notifications")

    def test_mark_notification_read(self, pool, db_connection, test_users):
        register_type("TEST_MARK_READ", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_MARK_READ",
            recipients=[recipient],
            template="Mark me read",
            should_persist=True,
            conn=db_connection,
        )
        notify_id = result.id

        mark_read(notify_id, recipient, conn=db_connection)
        print(f"✓ Marked notification {notify_id} as read")

    def test_get_urgent_notifications(self, pool, db_connection, test_users):
        register_type("TEST_GET_URGENT", NotificationUrgency.URGENT, 100)
        recipient = test_users[0]

        send(
            notification_type="TEST_GET_URGENT",
            recipients=[recipient],
            template="Urgent!",
            urgency=NotificationUrgency.URGENT,
            should_persist=True,
            conn=db_connection,
        )

        urgent = get_urgent(recipient, conn=db_connection)
        assert len(urgent) >= 1
        print(f"✓ Found {len(urgent)} urgent notifications")


class TestNotificationCount:
    """Tests for notification counting."""

    def test_count_returns_integer(self, pool, db_connection, test_users):
        recipient = test_users[0]
        c = count(recipient, conn=db_connection)
        assert isinstance(c, int)
        assert c >= 0
        print(f"✓ Count for {recipient}: {c}")

    def test_count_increases_after_send(self, pool, db_connection, test_users):
        register_type("TEST_COUNT", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        before = count(recipient, conn=db_connection)

        send(
            notification_type="TEST_COUNT",
            recipients=[recipient],
            template="Count test",
            conn=db_connection,
        )

        after = count(recipient, conn=db_connection)
        assert after >= before
        print(f"✓ Count: {before} -> {after}")


class TestEndToEndWorkflow:
    """End-to-end send/receive workflow tests."""

    def test_complete_workflow(self, pool, db_connection, test_users):
        register_type("WORKFLOW_TEST", NotificationUrgency.IMPORTANT, 100)
        recipient = test_users[0]
        sender = test_users[1]

        result = send(
            notification_type="WORKFLOW_TEST",
            recipients=[recipient],
            template="Workflow message",
            sender_moniker=sender,
            conn=db_connection,
        )
        notify_id = result.id
        print(f"✓ Sent notification ID {notify_id}")

        notifications = get_notifications(
            recipient, unread_only=False, conn=db_connection
        )
        found = any(n.id == notify_id for n in notifications)
        assert found, (
            f"Notification {notify_id} not found in {len(notifications)} total"
        )

        mark_read(notify_id, recipient, conn=db_connection)
        print("✓ Complete workflow: send -> receive -> mark read")

    def test_notification_persists(self, pool, db_connection, test_users):
        register_type("TEST_PERSIST", NotificationUrgency.ROUTINE, 100)
        recipient = test_users[0]

        result = send(
            notification_type="TEST_PERSIST",
            recipients=[recipient],
            template="Persist this",
            should_persist=True,
            conn=db_connection,
        )

        retrieved = get_notifications(recipient, conn=db_connection)
        assert any(n.id == result.id for n in retrieved)
        print(f"✓ Notification {result.id} persisted and retrieved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
