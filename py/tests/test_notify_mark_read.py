"""
Tests for marking notifications as read.

Key patterns:
- Always pass conn=conn to notify functions to keep operations in test transaction
- Use unique type names per test to avoid "already registered" errors
- Let test_transaction fixture handle cleanup via rollback
"""

import pytest
from bbsengine6.notify import (
    NotificationUrgency,
    send,
    get_notifications,
    mark_read,
    register_type,
)


class TestMarkRead:
    """Tests for mark_read function with proper connection handling."""

    @pytest.fixture
    def conn(self, db_connection):
        """Provide a connection that properly participates in test transactions."""
        db_connection.rollback()
        return db_connection

    def test_mark_read_single_notification(self, conn):
        """Mark a single notification as read."""
        type_name = "TEST_SINGLE"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Test message",
            should_persist=True,
            conn=conn,
        )

        notifications = get_notifications("jam", limit=10, conn=conn)
        current = [n for n in notifications if n.notification_type == type_name]
        assert len(current) >= 1
        assert notifications[0].read_by == {}

        mark_read(result.id, "jam", conn=conn)

        notifications_after = get_notifications("jam", limit=10, conn=conn)
        marked = [n for n in notifications_after if n.id == result.id]
        assert len(marked) == 1
        assert "jam" in marked[0].read_by

    def test_mark_read_updates_dateread(self, conn):
        """Verify mark_read sets dateread timestamp."""
        type_name = "TEST_DATEREAD"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Test message",
            should_persist=True,
            conn=conn,
        )

        mark_read(result.id, "jam", conn=conn)

        notifications = get_notifications("jam", limit=10, conn=conn)
        assert notifications[0].read_by["jam"] is not None

    def test_mark_read_invalid_id(self, conn):
        """mark_read with invalid ID raises ValueError."""
        type_name = "TEST_INVALID_ID"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        with pytest.raises(ValueError):
            mark_read(-1, "jam", conn=conn)
        with pytest.raises(ValueError):
            mark_read(0, "jam", conn=conn)
        with pytest.raises(ValueError):
            mark_read("not_an_int", "jam", conn=conn)

    def test_mark_read_invalid_moniker(self, conn):
        """mark_read with empty moniker raises ValueError (len > 255 silently passes)."""
        type_name = "TEST_INVALID_MONIKER"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Test message",
            should_persist=True,
            conn=conn,
        )
        with pytest.raises(ValueError, match="Invalid moniker"):
            mark_read(result.id, "", conn=conn)
        mark_read(result.id, "x" * 100, conn=conn)

    def test_mark_read_nonexistent_notification(self, conn):
        """Marking a non-existent notification as read should not raise."""
        type_name = "TEST_NONE"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        mark_read(999999, "jam", conn=conn)

    def test_mark_read_with_multiple_recipients(self, conn):
        """Test marking read for notifications with multiple recipients."""
        type_name = "TEST_MULTI_RECIP"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        result = send(
            notification_type=type_name,
            recipients=["alice", "bob"],
            template="Message for both",
            should_persist=True,
            conn=conn,
        )

        mark_read(result.id, "alice", conn=conn)

        alice_notifs = get_notifications("alice", limit=10, conn=conn)
        bob_notifs = get_notifications("bob", limit=10, conn=conn)

        assert "alice" in alice_notifs[0].read_by
        assert "bob" not in bob_notifs[0].read_by

    def test_mark_read_idempotent(self, conn):
        """Marking the same notification read multiple times should be safe."""
        type_name = "TEST_IDEMPOTENT"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Test message",
            should_persist=True,
            conn=conn,
        )

        mark_read(result.id, "jam", conn=conn)
        mark_read(result.id, "jam", conn=conn)
        mark_read(result.id, "jam", conn=conn)

        notifications = get_notifications("jam", limit=10, conn=conn)
        assert "jam" in notifications[0].read_by

    def test_mark_read_unread_only_filter(self, conn):
        """Test that marking read filters notifications correctly."""
        type_name = "TEST_UNREAD_FILTER"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        result1 = send(
            notification_type=type_name,
            recipients=["alice"],
            template="First message",
            should_persist=True,
            conn=conn,
        )
        result2 = send(
            notification_type=type_name,
            recipients=["alice"],
            template="Second message",
            should_persist=True,
            conn=conn,
        )

        all_before = get_notifications("alice", limit=10, conn=conn)
        unread_before = [n for n in all_before if n.id in (result1.id, result2.id)]
        unread_before_ids = {n.id for n in unread_before if "alice" not in n.read_by}
        assert result1.id in unread_before_ids
        assert result2.id in unread_before_ids

        mark_read(result1.id, "alice", conn=conn)

        all_after = get_notifications("alice", limit=10, conn=conn)
        unread_after = [n for n in all_after if n.id in (result1.id, result2.id)]
        unread_after_ids = {n.id for n in unread_after if "alice" not in n.read_by}

        assert result1.id not in unread_after_ids
        assert result2.id in unread_after_ids

    def test_mark_read_integration_with_send_and_get(self, conn):
        """Full integration: send, get, mark_read, verify."""
        type_name = "TEST_INTEGRATION"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        for i in range(3):
            send(
                notification_type=type_name,
                recipients=["alice"],
                template=f"Message {i}",
                should_persist=True,
                conn=conn,
            )

        notifications = get_notifications("alice", limit=10, conn=conn)
        current_type = [n for n in notifications if n.notification_type == type_name]
        unread = [n for n in current_type if "alice" not in n.read_by]
        assert len(unread) == 3

        for n in unread:
            mark_read(n.id, "alice", conn=conn)

        notifications_after = get_notifications("alice", limit=10, conn=conn)
        current_type_after = [
            n for n in notifications_after if n.notification_type == type_name
        ]
        unread_after = [n for n in current_type_after if "alice" not in n.read_by]
        assert len(unread_after) == 0

        assert all("alice" in n.read_by for n in current_type_after)


class TestMarkReadEdgeCases:
    """Edge case tests for mark_read."""

    @pytest.fixture
    def conn(self, db_connection):
        db_connection.rollback()
        return db_connection

    def test_mark_read_with_explicit_urgency(self, conn):
        """Test mark_read with explicitly set urgency."""
        type_name = "TEST_EXPLICIT_URGENCY"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.URGENT,
            max_per_hour=100,
            conn=conn,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Urgent message",
            urgency=NotificationUrgency.CRITICAL,
            should_persist=True,
            conn=conn,
        )
        mark_read(result.id, "jam", conn=conn)

    def test_mark_read_with_data(self, conn):
        """Test mark_read when notification has data payload."""
        type_name = "TEST_WITH_DATA"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Message with data",
            data={"key": "value", "count": 42},
            should_persist=True,
            conn=conn,
        )
        mark_read(result.id, "jam", conn=conn)

    def test_mark_read_none_connection(self, conn):
        """Test that mark_read works with conn=None (creates its own connection)."""
        type_name = "TEST_NONE_CONN"
        register_type(
            type_name=type_name,
            default_urgency=NotificationUrgency.ROUTINE,
            max_per_hour=100,
            conn=conn,
        )

        result = send(
            notification_type=type_name,
            recipients=["jam"],
            template="Test",
            should_persist=True,
            conn=conn,
        )
        conn.commit()
        mark_read(result.id, "jam", conn=None)
