# test_message_lib.py
# Tests for the message system DAL (Phase 1B)

import pytest
from unittest.mock import MagicMock, patch


class TestMessageLib:
    """Tests for message DAL functions (unit tests with mocks)."""

    def test_message_module_imports(self):
        """Message module can be imported."""
        from bbsengine6 import message

        assert hasattr(message, "store_message")
        assert hasattr(message, "get_pending_messages")
        assert hasattr(message, "mark_delivered")
        assert hasattr(message, "mark_read")
        assert hasattr(message, "get_unread_count")
        assert hasattr(message, "deliver_pending_on_connect")

    def test_message_enabled_by_default(self):
        """Message system is enabled by default."""
        from bbsengine6 import message

        assert message.is_enabled() is True

    def test_message_disable_enable(self):
        """Can disable and re-enable message system."""
        from bbsengine6 import message

        message.disable()
        assert message.is_enabled() is False
        message.enable()
        assert message.is_enabled() is True

    @patch("bbsengine6.message.record_message_sent")
    @patch("bbsengine6.message.is_blocked", return_value=False)
    @patch("bbsengine6.message.check_rate_limit", return_value=(True, 999))
    @patch("bbsengine6.message.getpool")
    def test_store_message(self, mock_getpool, mock_rate, mock_block, mock_record):
        """Store message in database."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (123,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        msg_id = message.store_message(
            channel="casino:table:blackjack-1",
            sender_moniker="alice",
            content="Hello table!",
            recipient_monikers=["bob", "charlie"],
        )

        assert msg_id == 123
        mock_cursor.execute.assert_called()

    @patch("bbsengine6.message.getpool")
    def test_get_pending_messages(self, mock_getpool):
        """Get pending messages for a user."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (
                1,
                "casino:table:blackjack-1",
                "alice",
                "Hello",
                None,
                "ROUTINE",
                None,
                None,
                "2024-01-01 12:00:00",
                "pending",
                None,
                None,
            ),
            (
                2,
                "member:bob",
                "charlie",
                "Hi there",
                None,
                "IMPORTANT",
                None,
                None,
                "2024-01-01 12:01:00",
                "delivered",
                "2024-01-01 12:02:00",
                None,
            ),
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        messages = message.get_pending_messages("bob")

        assert len(messages) == 2
        assert messages[0]["channel"] == "casino:table:blackjack-1"
        assert messages[0]["status"] == "pending"
        assert messages[1]["status"] == "delivered"

    @patch("bbsengine6.message.getpool")
    def test_mark_delivered(self, mock_getpool):
        """Mark message as delivered."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        message.mark_delivered(123, "bob")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("bbsengine6.message.getpool")
    def test_mark_read(self, mock_getpool):
        """Mark message as read."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        message.mark_read(123, "bob")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch("bbsengine6.message.getpool")
    def test_get_unread_count(self, mock_getpool):
        """Get count of unread messages."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (5,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        count = message.get_unread_count("bob")

        assert count == 5

    @patch("bbsengine6.message.get_pending_messages_prioritized")
    @patch("bbsengine6.message.mark_delivered")
    def test_deliver_pending_on_connect(self, mock_mark_delivered, mock_get_pending):
        """Deliver pending messages on connect."""
        from bbsengine6 import message

        mock_get_pending.return_value = [
            {"id": 1, "channel": "test", "content": "msg1"},
            {"id": 2, "channel": "test2", "content": "msg2"},
        ]

        messages = message.deliver_pending_on_connect("bob")

        assert len(messages) == 2
        assert mock_mark_delivered.call_count == 2

    def test_disabled_message_system_returns_empty(self):
        """When disabled, message functions return empty/default values."""
        from bbsengine6 import message

        message.disable()

        assert message.get_pending_messages("bob") == []
        assert message.get_unread_count("bob") == 0
        assert message.store_message("test", "a", "msg") == 0

        message.enable()


class TestStoreMessageWithChecks:
    """Tests for store_message / store_message_with_checks (rate limit
    and blocking wired in)."""

    @patch("bbsengine6.message.record_message_sent")
    @patch("bbsengine6.message.is_blocked")
    @patch("bbsengine6.message.check_rate_limit")
    @patch("bbsengine6.message.getpool")
    def test_happy_path_returns_id_and_recipients(
        self, mock_getpool, mock_rate, mock_block, mock_record
    ):
        from bbsengine6 import message

        mock_rate.return_value = (True, 100)
        mock_block.return_value = False
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (777,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        result = message.store_message_with_checks(
            channel="casino:table:bj1",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob", "charlie"],
        )

        assert result["message_id"] == 777
        assert result["rate_limit_ok"] is True
        assert result["recipients_stored"] == ["bob", "charlie"]
        assert result["recipients_blocked"] == []
        mock_record.assert_called_once()

    @patch("bbsengine6.message.is_blocked")
    @patch("bbsengine6.message.check_rate_limit")
    @patch("bbsengine6.message.getpool")
    def test_blocked_recipient_is_dropped(self, mock_getpool, mock_rate, mock_block):
        from bbsengine6 import message

        mock_rate.return_value = (True, 100)
        # bob has blocked alice
        mock_block.side_effect = lambda blocker, blocked, database=None: (
            blocker == "bob" and blocked == "alice"
        )
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (888,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        result = message.store_message_with_checks(
            channel="member:direct",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob", "charlie"],
        )

        assert result["message_id"] == 888
        assert "bob" in result["recipients_blocked"]
        assert "bob" not in result["recipients_stored"]
        assert "charlie" in result["recipients_stored"]

    @patch("bbsengine6.message.is_blocked")
    @patch("bbsengine6.message.check_rate_limit")
    @patch("bbsengine6.message.getpool")
    def test_rate_limit_denies_storage(self, mock_getpool, mock_rate, mock_block):
        from bbsengine6 import message

        mock_rate.return_value = (False, 0)
        mock_block.return_value = False
        mock_conn = MagicMock()
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        result = message.store_message_with_checks(
            channel="system:shout",
            sender_moniker="alice",
            content="spam",
            recipient_monikers=["bob"],
        )

        assert result["message_id"] == 0
        assert result["rate_limit_ok"] is False
        assert result["recipients_stored"] == []
        # The pool was never opened: rate-limit check happens first
        mock_pool.connection.assert_not_called()

    @patch("bbsengine6.message.getpool")
    def test_disabled_system_returns_zero(self, mock_getpool):
        from bbsengine6 import message

        message.disable()
        try:
            result = message.store_message_with_checks(
                channel="x", sender_moniker="alice", content="hi"
            )
            assert result["message_id"] == 0
            assert result["recipients_stored"] == []
        finally:
            message.enable()

    @patch("bbsengine6.message.record_message_sent")
    @patch("bbsengine6.message.is_blocked", return_value=False)
    @patch("bbsengine6.message.check_rate_limit", return_value=(True, 999))
    @patch("bbsengine6.message.getpool")
    def test_legacy_store_message_returns_int(
        self, mock_getpool, mock_rate, mock_block, mock_record
    ):
        from bbsengine6 import message

        mock_rate.return_value = (True, 100)
        mock_block.return_value = False
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1234,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        msg_id = message.store_message(
            channel="x",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob"],
        )
        assert isinstance(msg_id, int)
        assert msg_id == 1234


class TestPendingMessagesPrioritized:
    """CRITICAL/URGENT messages are surfaced before ROUTINE ones."""

    @patch("bbsengine6.message.getpool")
    def test_query_uses_urgency_first_ordering(self, mock_getpool):
        """The SQL must include a CASE expression over urgency."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        message.get_pending_messages_prioritized("bob")

        # Inspect the SQL passed to cur.execute.
        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "CRITICAL" in executed_sql
        assert "URGENT" in executed_sql
        assert "ROUTINE" in executed_sql
        assert "CASE m.urgency" in executed_sql
        assert "m.datestamp DESC" in executed_sql

    @patch("bbsengine6.message.getpool")
    def test_legacy_query_uses_datestamp_only(self, mock_getpool):
        """Sanity: get_pending_messages still uses datestamp-only ordering."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        message.get_pending_messages("bob")

        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "CASE m.urgency" not in executed_sql
        assert "m.datestamp DESC" in executed_sql

    @patch("bbsengine6.message.getpool")
    def test_prioritized_returns_rows(self, mock_getpool):
        from bbsengine6 import message

        rows = [
            (
                1,
                "x",
                "alice",
                "hi",
                None,
                "ROUTINE",
                None,
                None,
                "2024-01-01 12:00:00",
                "pending",
                None,
                None,
            ),
        ]
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_getpool.return_value = mock_pool

        msgs = message.get_pending_messages_prioritized("bob")
        assert len(msgs) == 1
        assert msgs[0]["urgency"] == "ROUTINE"

    def test_disabled_returns_empty(self):
        from bbsengine6 import message

        message.disable()
        try:
            assert message.get_pending_messages_prioritized("bob") == []
        finally:
            message.enable()


# =============================================================================
# Phase 1C: Groups, Blocking, Rate Limiting Tests
# =============================================================================


class TestMessageGroups:
    """Tests for message groups (Phase 1C)."""

    @patch("bbsengine6.message.getpool")
    def test_create_message_group(self, mock_getpool):
        """Create a message group."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (42,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        group_id = message.create_message_group(
            name="test-group",
            createdby="alice",
            description="Test group",
        )

        assert group_id == 42

    @patch("bbsengine6.message.getpool")
    def test_add_to_message_group(self, mock_getpool):
        """Add member to message group."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.add_to_message_group(
            group_id=1,
            member_moniker="bob",
            addedby="alice",
        )

        assert result is True

    @patch("bbsengine6.message.getpool")
    def test_get_message_group_members(self, mock_getpool):
        """Get members of a message group."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("alice",), ("bob",), ("charlie",)]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        members = message.get_message_group_members(group_id=1)

        assert members == ["alice", "bob", "charlie"]

    @patch("bbsengine6.message.getpool")
    def test_get_user_groups(self, mock_getpool):
        """Get groups a user belongs to."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            (1, "admins", "Admin group", "2024-01-01"),
            (2, "vips", "VIP players", "2024-01-02"),
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        groups = message.get_user_groups("alice")

        assert len(groups) == 2
        assert groups[0]["name"] == "admins"
        assert groups[1]["name"] == "vips"


class TestMessageBlocking:
    """Tests for message blocking (Phase 1C)."""

    @patch("bbsengine6.message.getpool")
    def test_block_sender(self, mock_getpool):
        """Block a sender."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.block_sender("alice", "bob")

        assert result is True

    @patch("bbsengine6.message.getpool")
    def test_unblock_sender(self, mock_getpool):
        """Unblock a sender."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.unblock_sender("alice", "bob")

        assert result is True

    @patch("bbsengine6.message.getpool")
    def test_is_blocked(self, mock_getpool):
        """Check if sender is blocked."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)  # Blocked
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.is_blocked("alice", "bob")

        assert result is True

    @patch("bbsengine6.message.getpool")
    def test_is_not_blocked(self, mock_getpool):
        """Check if sender is not blocked."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Not blocked
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.is_blocked("alice", "bob")

        assert result is False


class TestMessageRateLimiting:
    """Tests for rate limiting (Phase 1C)."""

    @patch("bbsengine6.message.getpool")
    def test_check_rate_limit_unlimited(self, mock_getpool):
        """Unlimited message type allows all."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)  # Unlimited
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        allowed, remaining = message.check_rate_limit("alice", "system:announcements")

        assert allowed is True
        assert remaining == 999

    @patch("bbsengine6.message.getpool")
    def test_check_rate_limit_allowed(self, mock_getpool):
        """Rate limit not exceeded."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (60,),  # Rate limit
            (5,),  # Current count
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        allowed, remaining = message.check_rate_limit("alice", "system:shout")

        assert allowed is True
        assert remaining == 55

    @patch("bbsengine6.message.getpool")
    def test_check_rate_limit_exceeded(self, mock_getpool):
        """Rate limit exceeded."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (60,),  # Rate limit
            (60,),  # Current count = limit
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        allowed, remaining = message.check_rate_limit("alice", "system:shout")

        assert allowed is False
        assert remaining == 0

    @patch("bbsengine6.message.getpool")
    def test_record_message_sent(self, mock_getpool):
        """Record message sent."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        result = message.record_message_sent("alice", "system:shout")

        assert result is True

    @patch("bbsengine6.message.getpool")
    def test_get_message_type_rate_limit(self, mock_getpool):
        """Get rate limit for message type."""
        from bbsengine6 import message

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (60,)
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool = MagicMock()
        mock_pool.connection.return_value.__enter__.return_value = mock_conn
        mock_pool.connection.return_value.__exit__.return_value = None
        mock_getpool.return_value = mock_pool

        limit = message.get_message_type_rate_limit("system:shout")

        assert limit == 60


# =============================================================================
# Integration Tests - require real database (zoid6test) with message tables
# =============================================================================


@pytest.mark.integration
class TestMessageLibIntegration:
    """Integration tests for message DAL with real database.

    These tests require the message tables to exist. Run the SQL first:
        psql -d zoid6test -f bbsengine6/py/src/bbsengine6/sql/message.sql
    """

    def test_store_and_retrieve_message(self, pool, db_connection):
        """Store message and retrieve it - REQUIRES engine.__message table."""
        pytest.skip("Requires message schema: psql -d zoid6test -f sql/message.sql")
        from bbsengine6 import message

        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO engine.__message 
                    (channel, sender_moniker, content)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    ("casino:table:blackjack-1", "alice", "Hello table!"),
                )
                msg_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO engine.__message_recipient (message_id, recipient_moniker)
                    VALUES (%s, %s)
                    """,
                    (msg_id, "bob"),
                )
                conn.commit()

        messages = message.get_pending_messages("bob", database="zoid6test")
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello table!"
        assert messages[0]["sender_moniker"] == "alice"

    def test_mark_delivered_and_read(self, pool, db_connection):
        """Test marking messages as delivered and read - REQUIRES engine.__message table."""
        pytest.skip("Requires message schema: psql -d zoid6test -f sql/message.sql")

    def test_unread_count(self, pool, db_connection):
        """Test unread message count - REQUIRES engine.__message table."""
        pytest.skip("Requires message schema: psql -d zoid6test -f sql/message.sql")

    def test_deliver_pending_on_connect(self, pool, db_connection):
        """Test delivering pending messages on connect - REQUIRES engine.__message table."""
        pytest.skip("Requires message schema: psql -d zoid6test -f sql/message.sql")


# =============================================================================
# Phase 1E: Templating Tests
# =============================================================================


class TestMessageTemplating:
    """Tests for message templating (Phase 1E)."""

    def test_render_template_simple(self):
        """Simple variable substitution."""
        from bbsengine6.message import render_template

        result = render_template("Hello {name}!", {"name": "Alice"})

        assert result == "Hello Alice!"

    def test_render_template_multiple_vars(self):
        """Multiple variable substitution."""
        from bbsengine6.message import render_template

        template = "{greeting}, {name}! You have {count} messages."
        vars = {"greeting": "Hello", "name": "Bob", "count": 5}

        result = render_template(template, vars)

        assert result == "Hello, Bob! You have 5 messages."

    def test_render_template_dollar_syntax(self):
        """Dollar syntax for variables."""
        from bbsengine6.message import render_template

        result = render_template("Hello $name!", {"name": "Charlie"})

        assert result == "Hello Charlie!"

    def test_render_template_mixed_syntax(self):
        """Mixed curly and dollar syntax."""
        from bbsengine6.message import render_template

        result = render_template(
            "{greeting} $name!", {"greeting": "Hi", "name": "Dave"}
        )

        assert result == "Hi Dave!"

    def test_render_template_missing_var(self):
        """Missing variables stay as placeholders."""
        from bbsengine6.message import render_template

        result = render_template("Hello {name}! {missing}", {"name": "Eve"})

        assert result == "Hello Eve! {missing}"

    def test_render_template_empty_vars(self):
        """Empty template returns empty string."""
        from bbsengine6.message import render_template

        result = render_template("", {"name": "Frank"})

        assert result == ""

    def test_render_message_content_with_template(self):
        """Render message with template."""
        from bbsengine6.message import render_message_content

        result = render_message_content(
            content="Default",
            template="Welcome {name} to {place}!",
            template_vars={"name": "Grace", "place": "the BBS"},
        )

        assert result == "Welcome Grace to the BBS!"

    def test_render_message_content_without_template(self):
        """Render message without template returns content."""
        from bbsengine6.message import render_message_content

        result = render_message_content(
            content="Just a message",
            template=None,
            template_vars=None,
        )

        assert result == "Just a message"

    def test_parse_variables_from_content(self):
        """Parse variables from content."""
        from bbsengine6.message import parse_variables_from_content

        content = "Hello {name}, you have {count} messages from {sender}!"

        vars = parse_variables_from_content(content)

        assert "name" in vars
        assert "count" in vars
        assert "sender" in vars

    def test_get_builtin_variables(self):
        """Get built-in variables."""
        from bbsengine6.message import get_builtin_variables

        vars = get_builtin_variables()

        assert "year" in vars
        assert "month" in vars
        assert "day" in vars
        assert "date" in vars
        assert "time" in vars

    def test_validate_template_valid(self):
        """Validate a valid template."""
        from bbsengine6.message import validate_template

        valid, errors = validate_template("Hello {name}!")

        assert valid is True
        assert errors == []

    def test_validate_template_unmatched_curly(self):
        """Validate template with unmatched curly braces."""
        from bbsengine6.message import validate_template

        valid, errors = validate_template("Hello {name!")

        assert valid is False
        assert len(errors) > 0
