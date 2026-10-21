# test_message_lib.py
# Tests for the message system DAL (Phase 1B)

import pytest
from unittest.mock import MagicMock, patch



@pytest.mark.unit
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

    def test_store_message(self, message_dal_stubs):
        """store_message stores through the DAL and returns the new message id."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.try_reserve.return_value = (True, 9)
        dal_messages.store_message_with_recipients.return_value = 123

        msg_id = message.store_message(
            channel="casino:table:blackjack-1",
            sender_moniker="alice",
            content="Hello table!",
            recipient_monikers=["bob", "charlie"],
        )

        assert msg_id == 123
        dal_messages.store_message_with_recipients.assert_called_once()
        assert dal_messages.store_message_with_recipients.call_args.args[1] == "casino:table:blackjack-1"

    def test_get_pending_messages(self, message_dal_stubs):
        """Pending messages come from the DAL's non-prioritized list."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        dal_messages.list_pending_for_recipient.return_value = [
            {"id": 1, "channel": "casino:table:blackjack-1", "sender_moniker": "alice",
             "content": "Hello", "status": "pending"},
            {"id": 2, "channel": "casino:table:blackjack-1", "sender_moniker": "alice",
             "content": "Again", "status": "delivered"},
        ]

        messages = message.get_pending_messages("bob")

        assert [m["status"] for m in messages] == ["pending", "delivered"]
        assert dal_messages.list_pending_for_recipient.call_args.args[1] == "bob"

    def test_mark_delivered(self, message_dal_stubs):
        """Mark message as delivered: the service hands the DAL the message and recipient."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.mark_delivered(123, "bob")

        dal_messages.mark_delivered.assert_called_once()
        assert dal_messages.mark_delivered.call_args.args[1:] == (123, "bob")

    def test_mark_read(self, message_dal_stubs):
        """Mark message as read: the service hands the DAL the message and recipient."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.mark_read(123, "bob")

        dal_messages.mark_read.assert_called_once()
        assert dal_messages.mark_read.call_args.args[1:] == (123, "bob")

    def test_get_unread_count(self, message_dal_stubs):
        """Unread count returns what the DAL counts for the recipient."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        dal_messages.count_unread_for_recipient.return_value = 5

        assert message.get_unread_count("bob") == 5
        dal_messages.count_unread_for_recipient.assert_called_once()

    @patch("bbsengine6.message.service.dal_messages")
    def test_deliver_pending_on_connect(self, mock_dal):
        """Deliver only never-delivered messages on connect, in one batch."""
        from bbsengine6 import message

        mock_dal.list_undelivered_for_recipient.return_value = [
            {"id": 1, "channel": "test", "content": "msg1"},
            {"id": 2, "channel": "test2", "content": "msg2"},
        ]

        messages = message.deliver_pending_on_connect("bob")

        assert len(messages) == 2
        mock_dal.list_undelivered_for_recipient.assert_called_once()
        mock_dal.mark_delivered_batch.assert_called_once()
        call_args = mock_dal.mark_delivered_batch.call_args[0]
        assert call_args[1] == [1, 2]
        assert call_args[2] == "bob"

    @patch("bbsengine6.message.service.dal_messages")
    def test_deliver_pending_on_connect_skips_batch_when_empty(self, mock_dal):
        """No pending rows means no UPDATE round trip."""
        from bbsengine6 import message

        mock_dal.list_undelivered_for_recipient.return_value = []

        assert message.deliver_pending_on_connect("bob") == []
        mock_dal.mark_delivered_batch.assert_not_called()

    def test_disabled_message_system_returns_empty(self):
        """When disabled, message functions return empty/default values."""
        from bbsengine6 import message

        message.disable()

        assert message.get_pending_messages("bob") == []
        assert message.get_unread_count("bob") == 0
        assert message.store_message("test", "a", "msg") == 0

        message.enable()


@pytest.mark.unit
class TestStoreMessageWithChecks:
    """Tests for store_message / store_message_with_checks (rate limit
    and blocking wired in)."""

    def test_happy_path_returns_id_and_recipients(self, message_dal_stubs):
        """A message that passes checks is stored and its id returned."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.try_reserve.return_value = (True, 100)
        dal_messages.store_message_with_recipients.return_value = 777

        result = message.store_message_with_checks(
            channel="member:direct",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob"],
        )

        assert result["message_id"] == 777
        assert result["rate_limit_ok"] is True

    def test_blocked_recipient_is_dropped(self, message_dal_stubs):
        """A recipient who blocked the sender is dropped; the others are kept."""
        from bbsengine6 import message
        from bbsengine6.message.dal import blocking as dal_blocking
        from bbsengine6.message.dal import messages as dal_messages
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.try_reserve.return_value = (True, 99)
        # bob has blocked alice; charlie has not.
        dal_blocking.is_blocked.side_effect = lambda args, blocker, blocked: (
            blocker == "bob" and blocked == "alice"
        )
        dal_messages.store_message_with_recipients.return_value = 888

        message.store_message_with_checks(
            channel="member:direct",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob", "charlie"],
        )

        kept = dal_messages.store_message_with_recipients.call_args.args[-1]
        assert kept == ["charlie"]

    @patch("bbsengine6.message.service.is_blocked")
    @patch("bbsengine6.message.service.check_rate_limit")
    @patch("bbsengine6.message.lib.getpool")
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

    @patch("bbsengine6.message.lib.getpool")
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

    def test_legacy_store_message_returns_int(self, message_dal_stubs):
        """store_message returns the message id as an int."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.try_reserve.return_value = (True, 100)
        dal_messages.store_message_with_recipients.return_value = 321

        assert message.store_message(
            channel="member:direct", sender_moniker="alice", content="hi",
            recipient_monikers=["bob"],
        ) == 321

@pytest.mark.unit
class TestPendingMessagesPrioritized:
    """CRITICAL/URGENT messages are surfaced before ROUTINE ones."""

    def test_query_uses_urgency_first_ordering(self, message_dal_stubs):
        """The prioritized read asks the DAL for urgency ordering."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.get_pending_messages_prioritized("bob")

        assert dal_messages.list_pending_for_recipient.call_args.kwargs["prioritized"] is True

    def test_legacy_query_uses_datestamp_only(self, message_dal_stubs):
        """The legacy read asks the DAL for datestamp ordering only."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        message.get_pending_messages("bob")

        assert dal_messages.list_pending_for_recipient.call_args.kwargs["prioritized"] is False

    def test_prioritized_returns_rows(self, message_dal_stubs):
        """Prioritized rows come back from the DAL unchanged."""
        from bbsengine6 import message
        from bbsengine6.message.dal import messages as dal_messages

        rows = [{"id": 1, "urgency": "CRITICAL"}, {"id": 2, "urgency": "ROUTINE"}]
        dal_messages.list_pending_for_recipient.return_value = rows

        assert message.get_pending_messages_prioritized("bob") == rows

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


@pytest.mark.unit
class TestMessageGroups:
    """Tests for message groups (Phase 1C)."""

    def test_create_message_group(self, message_dal_stubs):
        """create_message_group returns the id the DAL creates."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups

        dal_groups.create.return_value = 42

        assert message.create_message_group("admins", createdby="alice") == 42
        dal_groups.create.assert_called_once()

    @patch("bbsengine6.message.lib.getpool")
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

    def test_get_message_group_members(self, message_dal_stubs):
        """Group members come from the DAL member listing."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups

        dal_groups.list_members.return_value = ["alice", "bob", "charlie"]

        assert message.get_message_group_members(1) == ["alice", "bob", "charlie"]
        dal_groups.list_members.assert_called_once()

    def test_get_user_groups(self, message_dal_stubs):
        """get_user_groups returns the groups the DAL lists for the member."""
        from bbsengine6 import message
        from bbsengine6.message.dal import groups as dal_groups

        dal_groups.list_user_groups.return_value = [
            {"id": 1, "name": "admins"},
            {"id": 2, "name": "vips"},
        ]

        groups = message.get_user_groups("alice")

        assert [g["name"] for g in groups] == ["admins", "vips"]

class TestMessageBlocking:
    """Tests for message blocking (Phase 1C)."""

    def test_block_sender(self, message_dal_stubs):
        """Blocking a sender is recorded through the DAL."""
        from bbsengine6 import message
        from bbsengine6.message.dal import blocking as dal_blocking

        message.block_sender("alice", "bob")

        dal_blocking.block.assert_called_once()
        assert dal_blocking.block.call_args.args[1:] == ("alice", "bob")

    @patch("bbsengine6.message.lib.getpool")
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

    def test_is_blocked(self, message_dal_stubs):
        """is_blocked answers from the DAL blocking check."""
        from bbsengine6 import message
        from bbsengine6.message.dal import blocking as dal_blocking

        dal_blocking.is_blocked.return_value = True

        assert message.is_blocked("alice", "bob") is True
        dal_blocking.is_blocked.assert_called_once()

    @patch("bbsengine6.message.lib.getpool")
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


@pytest.mark.unit
class TestMessageRateLimiting:
    """Tests for rate limiting (Phase 1C)."""

    def test_check_rate_limit_unlimited(self, message_dal_stubs):
        """A type with no limit is always allowed, reported through the DAL."""
        from bbsengine6 import message
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.check.return_value = (True, 999)

        allowed, remaining = message.check_rate_limit("alice", "casino_kick")

        assert allowed is True
        assert remaining == 999

    def test_check_rate_limit_allowed(self, message_dal_stubs):
        """A sender under the limit is allowed, with the DAL's remaining count."""
        from bbsengine6 import message
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.check.return_value = (True, 55)

        allowed, remaining = message.check_rate_limit("alice", "casino_kick")

        assert allowed is True
        assert remaining == 55

    @patch("bbsengine6.message.lib.getpool")
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

    @patch("bbsengine6.message.lib.getpool")
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

    def test_get_message_type_rate_limit(self, message_dal_stubs):
        """The per-type limit is read from the DAL."""
        from bbsengine6 import message
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        dal_ratelimit.get_type_limit.return_value = 60

        assert message.get_message_type_rate_limit("casino_kick") == 60
        dal_ratelimit.get_type_limit.assert_called_once()

INTEGRATION_DB = "zoid6test"
INTEGRATION_CHANNEL = "test:integration:messages"


def _integration_db_available() -> bool:
    """True only when the zoid6test message schema is present.

    The integration tests write, so they run only against the throwaway
    zoid6test database and only when its message tables exist. They never
    use the shared zoid6 fixtures.
    """
    import psycopg
    from bbsengine6.message import lib as message_lib

    try:
        with psycopg.connect(
            f"host={message_lib._make_args(INTEGRATION_DB).databasehost} "
            f"port=5432 dbname={INTEGRATION_DB} user=opencode",
            connect_timeout=3,
        ) as conn, conn.cursor() as cur:
            cur.execute("select to_regclass('engine.__message') is not null")
            return bool(cur.fetchone()[0])
    except Exception:
        return False


INTEGRATION_MEMBERS = ("alice", "bob", "carol", "dave", "erin", "charlie")


def _integration_connect():
    import psycopg

    return psycopg.connect(
        f"host=/var/run/postgresql port=5432 dbname={INTEGRATION_DB} user=opencode"
    )


@pytest.fixture
def integration_message_ids():
    """Seed the test members, collect message ids, and clean up afterwards.

    Members are created for the duration of the test and removed in teardown,
    so zoid6test is left as it was found. Messages are deleted by id first, so
    their recipient rows cascade and the member delete does not hit a foreign
    key.
    """
    ids: list[int] = []
    with _integration_connect() as conn, conn.cursor() as cur:
        for name in INTEGRATION_MEMBERS:
            cur.execute(
                "INSERT INTO engine.__member (moniker, email, approved) "
                "VALUES (%s, %s, true) ON CONFLICT (moniker) DO NOTHING",
                (name, f"{name}@integration.test"),
            )
        conn.commit()
    yield ids
    with _integration_connect() as conn, conn.cursor() as cur:
        if ids:
            cur.execute("DELETE FROM engine.__message WHERE id = ANY(%s)", (list(ids),))
        cur.execute(
            "DELETE FROM engine.__member WHERE moniker = ANY(%s) "
            "AND email LIKE %s",
            (list(INTEGRATION_MEMBERS), "%@integration.test"),
        )
        conn.commit()


@pytest.mark.integration
@pytest.mark.requires_db
@pytest.mark.skipif(
    not _integration_db_available(),
    reason="zoid6test message schema not present (run the bootstrap there)",
)
class TestMessageLibIntegration:
    """Message DAL against the real zoid6test database.

    Each test stores through the real service, reads back, and deletes the
    rows it created. The shared zoid6 fixtures are not used.
    """

    def _store(self, sender, content, recipients, ids):
        from bbsengine6 import message
        from bbsengine6.message.dal import ratelimit as dal_ratelimit

        # The rate-limit reservation is not what these tests check.
        with patch.object(
            dal_ratelimit, "try_reserve", return_value=(True, 999)
        ):
            msg_id = message.store_message(
                channel=INTEGRATION_CHANNEL,
                sender_moniker=sender,
                content=content,
                recipient_monikers=recipients,
                database=INTEGRATION_DB,
            )
        if msg_id:
            ids.append(msg_id)
        return msg_id

    def test_store_and_retrieve_message(self, integration_message_ids):
        from bbsengine6 import message

        self._store("alice", "Hello table!", ["bob"], integration_message_ids)

        messages = message.get_pending_messages("bob", database=INTEGRATION_DB)
        mine = [m for m in messages if m["channel"] == INTEGRATION_CHANNEL]
        assert len(mine) == 1
        assert mine[0]["content"] == "Hello table!"
        assert mine[0]["sender_moniker"] == "alice"

    def test_mark_delivered_and_read(self, integration_message_ids):
        from bbsengine6 import message

        msg_id = self._store("alice", "read me", ["carol"], integration_message_ids)
        message.mark_delivered(msg_id, "carol", database=INTEGRATION_DB)
        message.mark_read(msg_id, "carol", database=INTEGRATION_DB)

        import psycopg

        with psycopg.connect(
            f"host=/var/run/postgresql port=5432 dbname={INTEGRATION_DB} user=opencode"
        ) as conn, conn.cursor() as cur:
            cur.execute(
                "select status from engine.__message_recipient "
                "where message_id = %s and recipient_moniker = %s",
                (msg_id, "carol"),
            )
            assert cur.fetchone()[0] == "read"

    def test_unread_count(self, integration_message_ids):
        from bbsengine6 import message

        self._store("alice", "one", ["dave"], integration_message_ids)
        self._store("alice", "two", ["dave"], integration_message_ids)

        assert message.get_unread_count("dave", database=INTEGRATION_DB) >= 2

    def test_deliver_pending_on_connect(self, integration_message_ids):
        from bbsengine6 import message

        msg_id = self._store("alice", "on connect", ["erin"], integration_message_ids)

        delivered = message.deliver_pending_on_connect("erin", database=INTEGRATION_DB)

        assert msg_id in [m["id"] for m in delivered]
        # Delivered once: a second connect has nothing new for this message.
        again = message.deliver_pending_on_connect("erin", database=INTEGRATION_DB)
        assert msg_id not in [m["id"] for m in again]


# =============================================================================
# Phase 1E: Templating Tests
# =============================================================================


@pytest.mark.unit
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
