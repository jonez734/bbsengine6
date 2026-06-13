# notify/daemon/tests/test_storage.py
# Tests for storage functionality

import pytest
from unittest.mock import MagicMock
import json

from bbsengine6.notify.daemon import storage


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
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        assert "__notify_imap_state" in sql

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
            (
                1,
                "imap.message",
                ["user1"],
                "2026-05-18 10:00:00",
                42,
                '{"subject": "Test"}',
                "sent",
                None,
            ),
            (
                2,
                "user.login",
                ["user2"],
                "2026-05-18 10:01:00",
                43,
                '{"username": "user2"}',
                "sent",
                None,
            ),
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
            (
                1,
                "imap.message",
                ["user1"],
                "2026-05-18 10:00:00",
                42,
                '{"subject": "Test"}',
                "sent",
                None,
            ),
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
            (
                1,
                "test.event",
                ["u1"],
                "2026-05-18 10:00:00",
                None,
                '{"key": "value"}',
                "sent",
                None,
            ),
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
            (
                1,
                "test.event",
                ["u1"],
                "2026-05-18 10:00:00",
                None,
                "invalid json",
                "sent",
                None,
            ),
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
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Query failed")
        )

        with pytest.raises(storage.StorageError):
            storage.get_notification_history(mock_pool)


class TestStorageIntegration:
    """Integration tests with SQL verification and mocked PostgreSQL"""

    def test_ensure_schema_reads_sql_file(self):
        """ensure_schema reads and executes SQL from file"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        storage.ensure_schema(mock_pool)

        # Verify SQL was executed (captured call args)
        assert mock_cursor.execute.call_count == 1
        sql_executed = mock_cursor.execute.call_args[0][0]

        # Verify SQL contains expected table definitions
        assert "__notify_imap_state" in sql_executed
        assert "__notify_history" in sql_executed
        assert "CREATE TABLE IF NOT EXISTS" in sql_executed

    def test_get_last_uid_queries_correct_table(self):
        """get_last_uid executes correct SQL query"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = (42,)

        result = storage.get_last_uid(mock_pool, "Gmail", "INBOX")

        # Verify correct SQL and parameters were used
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "FROM engine.__notify_imap_state" in sql
        assert "max_uid" in sql
        assert "server = %s AND mailbox = %s" in sql
        assert params == ("Gmail", "INBOX")
        assert result == 42

    def test_set_last_uid_uses_upsert(self):
        """set_last_uid executes INSERT ON CONFLICT UPDATE"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        storage.set_last_uid(mock_pool, "Gmail", "INBOX", 100)

        # Verify upsert SQL
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT INTO engine.__notify_imap_state" in sql
        assert "ON CONFLICT" in sql
        assert "DO UPDATE" in sql
        assert params[0] == "Gmail"
        assert params[1] == "INBOX"
        assert params[2] == 100
        assert params[3] == 100  # Updated value

        # Verify commit was called
        mock_conn.commit.assert_called_once()

    def test_record_notification_inserts_with_json(self):
        """record_notification inserts notification with JSON data"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = (999,)

        template_vars = {"subject": "Test", "from": "sender@example.com"}

        result = storage.record_notification(
            mock_pool,
            "imap.message",
            ["user1", "user2"],
            template_vars,
            notification_id=42,
            status="sent",
        )

        # Verify INSERT SQL
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "INSERT INTO engine.__notify_history" in sql
        assert params[0] == "imap.message"
        assert params[1] == ["user1", "user2"]
        assert params[2] == 42

        # Verify JSON serialization
        json_data = json.loads(params[3])
        assert json_data == template_vars
        assert params[4] == "sent"

        # Verify return value
        assert result == 999
        mock_conn.commit.assert_called_once()

    def test_get_notification_history_without_filter(self):
        """get_notification_history queries all notifications"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchall.return_value = [
            (
                1,
                "imap.message",
                ["user1"],
                "2026-05-18 10:00:00",
                42,
                '{"subject": "Test"}',
                "sent",
                None,
            ),
        ]

        result = storage.get_notification_history(mock_pool, limit=100)

        # Verify SELECT SQL (no filter)
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "SELECT id, notification_type" in sql
        assert "FROM engine.__notify_history" in sql
        assert "WHERE notification_type" not in sql
        assert "ORDER BY datesent DESC" in sql
        assert params == (100,)

        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_get_notification_history_with_filter(self):
        """get_notification_history queries filtered by type"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchall.return_value = [
            (
                1,
                "imap.message",
                ["user1"],
                "2026-05-18 10:00:00",
                42,
                '{"subject": "Test"}',
                "sent",
                None,
            ),
        ]

        result = storage.get_notification_history(
            mock_pool,
            limit=50,
            notification_type="imap.message",
        )

        # Verify SELECT with WHERE clause
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "WHERE notification_type = %s" in sql
        assert params[0] == "imap.message"
        assert params[1] == 50

        assert len(result) == 1

    def test_get_notification_history_json_deserialization(self):
        """get_notification_history properly deserializes JSON data"""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        # Simulate database returning JSON and other columns
        test_data = {
            "subject": "Test Email",
            "from": "sender@example.com",
            "body": "Email body text",
            "timestamp": "2026-05-18T10:00:00Z",
        }

        mock_cursor.fetchall.return_value = [
            (
                1,
                "imap.message",
                ["user1", "user2"],
                "2026-05-18 10:00:00",
                42,
                json.dumps(test_data),  # Simulate JSONB from database
                "sent",
                None,
            ),
        ]

        result = storage.get_notification_history(mock_pool)

        # Verify JSON was properly deserialized
        assert len(result) == 1
        record = result[0]
        assert record["id"] == 1
        assert record["notification_type"] == "imap.message"
        assert record["recipients"] == ["user1", "user2"]
        assert record["status"] == "sent"
        assert record["data"] == test_data
        assert record["data"]["subject"] == "Test Email"
        assert record["data"]["from"] == "sender@example.com"

    def test_storage_connection_management(self):
        """Storage functions properly manage database connections"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Setup context manager chains
        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)

        mock_cursor.fetchone.return_value = (50,)

        # Call storage function
        storage.get_last_uid(mock_pool, "Test", "INBOX")

        # Verify connection lifecycle
        mock_pool.connection.assert_called_once()
        mock_conn.cursor.assert_called_once()

        # Verify context managers were entered/exited
        mock_pool.connection.return_value.__enter__.assert_called_once()
        mock_pool.connection.return_value.__exit__.assert_called_once()
        mock_conn.cursor.return_value.__enter__.assert_called_once()
        mock_conn.cursor.return_value.__exit__.assert_called_once()

    def test_storage_error_on_connection_failure(self):
        """Storage raises StorageError when connection fails"""
        mock_pool = MagicMock()
        mock_pool.connection.side_effect = Exception("Connection refused")

        with pytest.raises(storage.StorageError) as exc_info:
            storage.get_last_uid(mock_pool, "Test", "INBOX")

        assert "Failed to get last UID" in str(exc_info.value)

    def test_storage_error_on_query_failure(self):
        """Storage raises StorageError when query fails"""
        mock_pool = MagicMock()
        mock_conn = MagicMock()

        mock_pool.connection.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.connection.return_value.__exit__ = MagicMock(return_value=None)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            side_effect=Exception("Query syntax error")
        )

        with pytest.raises(storage.StorageError) as exc_info:
            storage.set_last_uid(mock_pool, "Test", "INBOX", 100)

        assert "Failed to set last UID" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
