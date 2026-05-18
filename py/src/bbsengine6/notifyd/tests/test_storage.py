# notifyd/tests/test_storage.py
# Tests for storage functionality

import pytest
from unittest import mock
from unittest.mock import MagicMock, patch, call
import json

from bbsengine6.notifyd import storage


class TestStorageError:
    """Test StorageError exception"""

    def test_storage_error_is_exception(self):
        """StorageError is an Exception"""
        error = storage.StorageError("Test error")
        assert isinstance(error, Exception)

    def test_storage_error_message(self):
        """StorageError preserves message"""
        error = storage.StorageError("Database connection failed")
        assert str(error) == "Database connection failed"


class TestEnsureSchema:
    """Test schema initialization"""

    def test_ensure_schema_success(self):
        """Schema is created successfully"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        storage.ensure_schema(mock_pool)
        
        # Verify schema SQL was executed
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_ensure_schema_failure(self):
        """Schema creation fails"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Database error")
        )
        
        with pytest.raises(storage.StorageError):
            storage.ensure_schema(mock_pool)


class TestGetLastUid:
    """Test retrieving last processed UID"""

    def test_get_last_uid_exists(self):
        """Get last UID when record exists"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchone.return_value = (42,)
        
        result = storage.get_last_uid(mock_pool, "Gmail", "INBOX")
        
        assert result == 42
        mock_cursor.execute.assert_called_once()
        # Verify correct SQL was executed
        call_args = mock_cursor.execute.call_args
        assert "notifyd_imap_state" in str(call_args[0][0])

    def test_get_last_uid_not_found(self):
        """Get last UID when no record exists returns 0"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchone.return_value = None
        
        result = storage.get_last_uid(mock_pool, "Gmail", "INBOX")
        
        assert result == 0

    def test_get_last_uid_query_fails(self):
        """Get last UID when query fails"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Query failed")
        )
        
        with pytest.raises(storage.StorageError):
            storage.get_last_uid(mock_pool, "Gmail", "INBOX")


class TestSetLastUid:
    """Test updating last processed UID"""

    def test_set_last_uid_insert(self):
        """Insert new UID record"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        storage.set_last_uid(mock_pool, "Gmail", "INBOX", 100)
        
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_set_last_uid_update(self):
        """Update existing UID record"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        storage.set_last_uid(mock_pool, "Gmail", "INBOX", 200)
        
        # Verify SQL contains ON CONFLICT
        call_args = mock_cursor.execute.call_args
        assert "ON CONFLICT" in str(call_args[0][0])

    def test_set_last_uid_query_fails(self):
        """Set last UID when query fails"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Update failed")
        )
        
        with pytest.raises(storage.StorageError):
            storage.set_last_uid(mock_pool, "Gmail", "INBOX", 100)


class TestRecordNotification:
    """Test recording notification history"""

    def test_record_notification_success(self):
        """Record notification to history"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchone.return_value = (999,)
        
        result = storage.record_notification(
            mock_pool,
            "imap.message",
            ["user1", "user2"],
            {"subject": "Test", "from": "test@example.com"},
            notification_id=42,
            status="sent",
        )
        
        assert result == 999
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    def test_record_notification_with_error(self):
        """Record failed notification with error message"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchone.return_value = (123,)
        
        result = storage.record_notification(
            mock_pool,
            "imap.message",
            ["user1"],
            {"error": "Connection timeout"},
            status="failed",
            error_message="IMAP connection timeout",
        )
        
        assert result == 123

    def test_record_notification_returns_zero_on_empty_response(self):
        """Record notification returns 0 if no ID returned"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchone.return_value = None
        
        result = storage.record_notification(
            mock_pool,
            "test.event",
            ["user1"],
            {},
        )
        
        assert result == 0

    def test_record_notification_query_fails(self):
        """Record notification when query fails"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Insert failed")
        )
        
        with pytest.raises(storage.StorageError):
            storage.record_notification(
                mock_pool,
                "test.event",
                ["user1"],
                {"data": "test"},
            )


class TestGetNotificationHistory:
    """Test retrieving notification history"""

    def test_get_notification_history_success(self):
        """Retrieve notification history"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        # Mock two notification records
        mock_cursor.fetchall.return_value = [
            (1, "imap.message", ["user1"], "2026-05-18 10:00:00", 42, '{"subject": "Test"}', "sent", None),
            (2, "user.login", ["user2"], "2026-05-18 10:01:00", 43, '{"username": "user2"}', "sent", None),
        ]
        
        result = storage.get_notification_history(mock_pool, limit=100)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["notification_type"] == "imap.message"
        assert result[0]["recipients"] == ["user1"]
        assert result[0]["status"] == "sent"
        assert result[1]["id"] == 2

    def test_get_notification_history_with_filter(self):
        """Retrieve notification history filtered by type"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchall.return_value = [
            (1, "imap.message", ["user1"], "2026-05-18 10:00:00", 42, '{"subject": "Test"}', "sent", None),
        ]
        
        result = storage.get_notification_history(
            mock_pool,
            limit=50,
            notification_type="imap.message",
        )
        
        assert len(result) == 1
        assert result[0]["notification_type"] == "imap.message"

    def test_get_notification_history_empty(self):
        """Get notification history when no records exist"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchall.return_value = []
        
        result = storage.get_notification_history(mock_pool)
        
        assert result == []

    def test_get_notification_history_parses_json(self):
        """Notification data is parsed from JSON"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchall.return_value = [
            (1, "test.event", ["u1"], "2026-05-18 10:00:00", None, '{"key": "value"}', "sent", None),
        ]
        
        result = storage.get_notification_history(mock_pool)
        
        assert result[0]["data"] == {"key": "value"}

    def test_get_notification_history_invalid_json(self):
        """Notification with invalid JSON uses empty dict"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchall.return_value = [
            (1, "test.event", ["u1"], "2026-05-18 10:00:00", None, "invalid json", "sent", None),
        ]
        
        result = storage.get_notification_history(mock_pool)
        
        assert result[0]["data"] == {}

    def test_get_notification_history_null_json(self):
        """Notification with NULL JSON uses empty dict"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        
        mock_cursor.fetchall.return_value = [
            (1, "test.event", ["u1"], "2026-05-18 10:00:00", None, None, "sent", None),
        ]
        
        result = storage.get_notification_history(mock_pool)
        
        assert result[0]["data"] == {}

    def test_get_notification_history_query_fails(self):
        """Get history when query fails"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Query failed")
        )
        
        with pytest.raises(storage.StorageError):
            storage.get_notification_history(mock_pool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
