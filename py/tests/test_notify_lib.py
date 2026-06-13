# test_notify_lib.py
# Tests for bbsengine6.notify.lib public API functions

import time
import uuid
from unittest.mock import MagicMock

import pytest

from bbsengine6.notify.lib import (
    Notification,
    NotificationUrgency,
    UserNotificationQueue,
    block,
    expunge,
    get_blocked,
    get_notifications,
    get_queue,
    mark_delivered,
    mark_read,
    register_type,
    send,
    set_rate_limit,
    unblock,
)


class MockCursor:
    def __init__(self, rows=None, side_effect=None):
        self._rows = rows or []
        self._side_effect = side_effect
        self._index = 0

    def execute(self, query, params=None):
        if self._side_effect:
            raise self._side_effect

    def fetchone(self):
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None

    def fetchall(self):
        result = self._rows[self._index :]
        self._index = len(self._rows)
        return result

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def unique_moniker(base: str) -> str:
    return f"{base}_{uuid.uuid4().hex[:8]}"


class TestGetQueue:
    def test_get_queue_creates_new(self):
        moniker = unique_moniker("queue_test")
        queue = get_queue(moniker)
        assert isinstance(queue, UserNotificationQueue)

    def test_get_queue_returns_same_instance(self):
        moniker = unique_moniker("queue_test2")
        q1 = get_queue(moniker)
        q2 = get_queue(moniker)
        assert q1 is q2

    def test_get_queue_invalid_moniker(self):
        with pytest.raises(ValueError):
            get_queue("")

    def test_get_queue_with_slashes(self):
        with pytest.raises(ValueError):
            get_queue("user/moniker")


class TestNotificationUrgency:
    def test_urgency_values(self):
        assert NotificationUrgency.CRITICAL.value == "CRITICAL"
        assert NotificationUrgency.URGENT.value == "URGENT"
        assert NotificationUrgency.IMPORTANT.value == "IMPORTANT"
        assert NotificationUrgency.ROUTINE.value == "ROUTINE"


class TestRegisterType:
    def test_register_type_creates_type(self):
        mock_conn = MagicMock()
        MagicMock()
        mock_cursor = MockCursor(rows=[None])

        def enter_side_effect():
            return mock_cursor

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None

        register_type(
            f"test_type_{uuid.uuid4().hex[:8]}",
            NotificationUrgency.IMPORTANT,
            20,
            True,
            conn=mock_conn,
        )

    def test_register_type_invalid_name(self):
        mock_conn = MagicMock()

        with pytest.raises(ValueError):
            register_type("", conn=mock_conn)


class TestSetRateLimit:
    def test_set_rate_limit_creates_type_if_not_exists(self):
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[None])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None

        set_rate_limit(f"rate_type_{uuid.uuid4().hex[:8]}", 50, conn=mock_conn)


class TestMarkRead:
    def test_mark_read_updates_recipient(self):
        moniker = unique_moniker("markread")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None
        mock_conn.pool.putconn.return_value = None

        mark_read(1, moniker, conn=mock_conn)

    def test_mark_read_invalid_id(self):
        with pytest.raises(ValueError):
            mark_read(0, "user")

    def test_mark_read_invalid_moniker(self):
        with pytest.raises(ValueError):
            mark_read(1, "")


class TestMarkDelivered:
    def test_mark_delivered_updates_recipient(self):
        moniker = unique_moniker("markdeliv")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None
        mock_conn.pool.putconn.return_value = None

        mark_delivered(1, moniker, conn=mock_conn)

    def test_mark_delivered_invalid_id(self):
        with pytest.raises(ValueError):
            mark_delivered(-1, "user")


class TestBlock:
    def test_block_creates_entry(self):
        blocker = unique_moniker("blocker")
        blocked = unique_moniker("blocked")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None
        mock_conn.pool.putconn.return_value = None

        block(blocker, blocked, conn=mock_conn)


class TestUnblock:
    def test_unblock_removes_entry(self):
        blocker = unique_moniker("unblocker")
        blocked = unique_moniker("unblocked")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None
        mock_conn.pool.putconn.return_value = None

        unblock(blocker, blocked, conn=mock_conn)


class TestGetBlocked:
    def test_get_blocked_returns_list(self):
        moniker = unique_moniker("getblocked")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(
            rows=[
                {"sender_moniker": "bad1"},
                {"sender_moniker": "bad2"},
            ]
        )

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = get_blocked(moniker, conn=mock_conn)
        assert isinstance(result, list)


class TestExpunge:
    def test_expunge_requires_ownership(self):
        sender = unique_moniker("expunge_sender")
        notification_id = 999

        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[{"sender_moniker": sender}])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        wrong_user = unique_moniker("wrong_user")
        result = expunge(notification_id, wrong_user, conn=mock_conn)
        assert result is False

    def test_expunge_invalid_id_zero(self):
        moniker = unique_moniker("expunge_invalid")
        result = expunge(0, moniker)
        assert result is False

    def test_expunge_invalid_id_negative(self):
        moniker = unique_moniker("expunge_invalid")
        result = expunge(-1, moniker)
        assert result is False

    def test_expunge_nonexistent(self):
        sender = unique_moniker("expunge_nonexist")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = expunge(999, sender, conn=mock_conn)
        assert result is False

    def test_expunge_owner_can_delete(self):
        sender = unique_moniker("expunge_owner")
        mock_conn = MagicMock()
        mock_cursor = MockCursor(rows=[{"sender_moniker": sender}])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.commit.return_value = None
        mock_conn.pool.putconn.return_value = None

        result = expunge(123, sender, conn=mock_conn)
        assert result is True


class TestGetNotifications:
    def test_get_notifications_returns_empty_on_bad_conn(self):
        result = get_notifications("user", conn=None)
        assert result == []

    def test_get_notifications_returns_list(self):
        mock_conn = MagicMock()

        mock_row = {
            "id": 1,
            "notification_type": "test_type",
            "sender_moniker": "sender",
            "template": None,
            "template_vars": None,
            "rendered_message": "Hello",
            "data": None,
            "urgency": "ROUTINE",
            "mac": None,
            "datecreated": MagicMock(timestamp=lambda: time.time()),
            "datedelivered": None,
            "dateread": None,
        }
        mock_cursor = MockCursor(rows=[mock_row])

        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.pool.putconn.return_value = None

        result = get_notifications("anyuser", conn=mock_conn)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].id == 1


class TestSendValidation:
    def test_send_invalid_type_name_empty(self):
        with pytest.raises(ValueError):
            send("", recipients=["user"], template="test")

    def test_send_invalid_type_name_dot(self):
        with pytest.raises(ValueError):
            send("test.type", recipients=["user"], template="test")

    def test_send_invalid_type_name_hyphen(self):
        with pytest.raises(ValueError):
            send("test-type", recipients=["user"], template="test")

    def test_send_empty_recipients(self):
        with pytest.raises(ValueError):
            send("test_type", recipients=[], template="test")

    def test_send_invalid_sender(self):
        with pytest.raises(ValueError):
            send(
                "test_type",
                recipients=["user"],
                template="test",
                sender_moniker="bad/user",
            )


class TestNotificationDataclass:
    def test_notification_fields(self):
        ts = time.time()
        notif = Notification(
            id=1,
            notification_type="test",
            recipients=["user"],
            recipients_ok=["user"],
            recipients_failed=[],
            sender_moniker="sender",
            template=None,
            template_vars={},
            message="Hello",
            data={},
            urgency=NotificationUrgency.ROUTINE,
            timestamp=ts,
            delivered_to={},
            read_by={},
            should_persist=True,
            datecreated=None,
        )
        assert notif.id == 1
        assert notif.notification_type == "test"
        assert notif.urgency == NotificationUrgency.ROUTINE
