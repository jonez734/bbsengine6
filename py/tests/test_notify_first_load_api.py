"""
Integration tests: Fresh schema notify subsystem API.

Tests the complete notify API cycle against a fresh schema created by
the console stage (checknotify + checknotifyd). This verifies that:
1. Console stage creates all tables/views correctly
2. notify/lib.py functions work against fresh schema
3. Daemon storage functions work against fresh schema

Run with: pytest py/tests/test_notify_first_load_api.py -xvs
"""

import getpass
import time

import pytest


@pytest.mark.integration
class TestFirstLoadSchema:
    """Verify all expected tables/views/types exist after fresh build."""

    def test_tables_exist(self, db_connection):
        """Verify all 8 notify tables exist."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'engine'
                AND tablename LIKE '__notify%'
                ORDER BY tablename
                """
            )
            tables = {r[0] for r in cur.fetchall()}

        expected = {
            "__notify",
            "__notify_block",
            "__notify_group",
            "__notify_history",
            "__notify_imap_state",
            "__notify_rate_limit",
            "__notify_recipient",
            "__notify_type",
        }
        missing = expected - tables
        assert not missing, f"Missing tables: {missing}"

    def test_views_exist(self, db_connection):
        """Verify all 4 notify views exist."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT viewname FROM pg_views
                WHERE schemaname = 'engine'
                AND viewname LIKE 'notify%'
                ORDER BY viewname
                """
            )
            views = {r[0] for r in cur.fetchall()}

        expected = {"notify", "notify_blocked", "notify_unread", "notify_urgent"}
        missing = expected - views
        assert not missing, f"Missing views: {missing}"

    def test_urgency_enum_exists(self, db_connection):
        """Verify notify_urgency_enum type exists."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_type
                WHERE typnamespace = (
                    SELECT oid FROM pg_namespace WHERE nspname = 'engine'
                )
                AND typname = 'notify_urgency_enum'
                """
            )
            assert cur.fetchone() is not None, "notify_urgency_enum type missing"

    def test_notify_recipient_has_date_columns(self, db_connection):
        """Verify __notify_recipient uses date* column names."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_recipient'
                ORDER BY column_name
                """
            )
            columns = {r[0] for r in cur.fetchall()}

        assert "datedelivered" in columns, "Missing datedelivered column"
        assert "dateread" in columns, "Missing dateread column"
        assert "added_at" not in columns, "Found old added_at column"
        assert "delivered_at" not in columns, "Found old delivered_at column"
        assert "read_at" not in columns, "Found old read_at column"

    def test_notify_group_has_dateadded(self, db_connection):
        """Verify __notify_group uses dateadded column."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_group'
                """
            )
            columns = {r[0] for r in cur.fetchall()}

        assert "dateadded" in columns, "Missing dateadded column"
        assert "added_at" not in columns, "Found old added_at column"

    def test_notify_type_has_dateregistered(self, db_connection):
        """Verify __notify_type uses dateregistered column."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_type'
                """
            )
            columns = {r[0] for r in cur.fetchall()}

        assert "dateregistered" in columns, "Missing dateregistered column"
        assert "registered_at" not in columns, "Found old registered_at column"

    def test_notify_imap_state_has_dateupdated(self, db_connection):
        """Verify __notify_imap_state uses dateupdated column."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_imap_state'
                """
            )
            columns = {r[0] for r in cur.fetchall()}

        assert "dateupdated" in columns, "Missing dateupdated column"
        assert "updated_at" not in columns, "Found old updated_at column"

    def test_notify_history_has_datesent(self, db_connection):
        """Verify __notify_history uses datesent column."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_history'
                """
            )
            columns = {r[0] for r in cur.fetchall()}

        assert "datesent" in columns, "Missing datesent column"
        assert "sent_at" not in columns, "Found old sent_at column"


@pytest.mark.integration
class TestNotifyAPIFullCycle:
    """Test the complete notify API cycle: send → get → mark delivered → mark read."""

    def test_register_type(self, db_connection):
        """Verify register_type() creates __notify_type with dateregistered."""
        from bbsengine6.notify import register_type
        from bbsengine6.notify import NotificationUrgency

        test_type = f"test_first_load_{int(time.time())}"

        result = register_type(test_type, NotificationUrgency.ROUTINE, 5, True)
        assert result is None, "register_type returns None"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT type_name, dateregistered IS NOT NULL
                FROM engine.__notify_type
                WHERE type_name = %s
                """,
                (test_type,),
            )
            row = cur.fetchone()

        assert row is not None, f"Type {test_type} not found"
        assert row[0] == test_type
        assert row[1] is True, "dateregistered should be set"

    def test_send_and_get_notifications(
        self, db_connection, create_test_users
    ):
        """Verify send() creates notification and get_notifications() retrieves it."""
        from bbsengine6.notify import send, get_notifications

        user = getpass.getuser()
        recipient = f"test_{user}_1"
        test_type = f"test_first_load_{int(time.time())}"

        from bbsengine6.notify import register_type
        from bbsengine6.notify import NotificationUrgency
        register_type(test_type, NotificationUrgency.ROUTINE, 5, True)

        notify_id = send(
            notification_type=test_type,
            recipients=[recipient],
            sender_moniker=recipient,
            message="Test notification",
            template="test",
            args=None,
        )
        assert notify_id is not None, "send() returned None"

        notifications = get_notifications(recipient, limit=50)
        assert len(notifications) > 0, "No notifications returned"

        # send() returns a Notification object, not an int
        found = any(n.id == notify_id.id for n in notifications)
        assert found, f"Notification {notify_id.id} not found in get_notifications()"

    def test_mark_delivered(
        self, db_connection, create_test_users
    ):
        """Verify mark_delivered() sets datedelivered on __notify_recipient."""
        from bbsengine6.notify import send, mark_delivered

        user = getpass.getuser()
        recipient = f"test_{user}_1"
        test_type = f"test_first_load_{int(time.time())}"

        from bbsengine6.notify import register_type
        from bbsengine6.notify import NotificationUrgency
        register_type(test_type, NotificationUrgency.ROUTINE, 5, True)

        notify_id = send(
            notification_type=test_type,
            recipients=[recipient],
            sender_moniker=recipient,
            message="Test",
            template="test",
            args=None,
        )

        result = mark_delivered(notify_id.id, recipient, None)
        assert result is None, "mark_delivered returns None"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT datedelivered IS NOT NULL
                FROM engine.__notify_recipient
                WHERE notify_id = %s AND recipient_moniker = %s
                """,
                (notify_id.id, recipient),
            )
            row = cur.fetchone()

        assert row is not None, "Recipient row not found"
        assert row[0] is True, "datedelivered should be set"

    def test_mark_read(
        self, db_connection, create_test_users
    ):
        """Verify mark_read() sets dateread on __notify_recipient."""
        from bbsengine6.notify import send, mark_read

        user = getpass.getuser()
        recipient = f"test_{user}_1"
        test_type = f"test_first_load_{int(time.time())}"

        from bbsengine6.notify import register_type
        from bbsengine6.notify import NotificationUrgency
        register_type(test_type, NotificationUrgency.ROUTINE, 5, True)

        notify_id = send(
            notification_type=test_type,
            recipients=[recipient],
            sender_moniker=recipient,
            message="Test",
            template="test",
            args=None,
        )

        result = mark_read(notify_id.id, recipient, None)
        assert result is None, "mark_delivered returns None"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT dateread IS NOT NULL
                FROM engine.__notify_recipient
                WHERE notify_id = %s AND recipient_moniker = %s
                """,
                (notify_id.id, recipient),
            )
            row = cur.fetchone()

        assert row is not None, "Recipient row not found"
        assert row[0] is True, "dateread should be set"

    def test_block_and_unblock(
        self, db_connection, create_test_users
    ):
        """Verify block() and unblock() manage __notify_block."""
        from bbsengine6.notify import block, unblock

        user = getpass.getuser()
        blocker = f"test_{user}_1"
        sender = f"test_{user}_2"

        block(blocker, sender, None)

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM engine.__notify_block
                WHERE blocker_moniker = %s AND sender_moniker = %s
                """,
                (blocker, sender),
            )
            row = cur.fetchone()

        assert row is not None, "Block entry should be created"

        unblock(blocker, sender, None)

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM engine.__notify_block
                WHERE blocker_moniker = %s AND sender_moniker = %s
                """,
                (blocker, sender),
            )
            row = cur.fetchone()

        assert row is None, "Block entry should be removed"

    def test_add_and_remove_group(
        self, db_connection, create_test_users
    ):
        """Verify create_group() and add_to_group() create __notify_group with dateadded."""
        user = getpass.getuser()
        test_users = [f"test_{user}_1", f"test_{user}_2"]
        group_name = f"test_group_{int(time.time())}"

        from bbsengine6.notify import create_group, add_to_group, get_group_members, remove_from_group

        create_group(group_name, test_users, None)

        members = get_group_members(group_name, None)
        assert len(members) == 2, f"Expected 2 members, got {len(members)}"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT dateadded IS NOT NULL
                FROM engine.__notify_group
                WHERE group_name = %s AND member_moniker = %s
                """,
                (group_name, test_users[0]),
            )
            row = cur.fetchone()

        assert row is not None, "Group entry not found"
        assert row[0] is True, "dateadded should be set"

        remove_from_group(group_name, test_users[0], None)
        # Verify removed
        members = get_group_members(group_name, None)
        assert len(members) == 1, f"Expected 1 member after removal, got {len(members)}"


@pytest.mark.integration
class TestDaemonStorageAPI:
    """Test daemon storage functions against fresh __notify_imap_state and __notify_history."""

    def test_imap_state_set_and_get(
        self, db_connection, create_test_users, pool
    ):
        """Verify set_last_uid() and get_last_uid() work on __notify_imap_state."""
        from bbsengine6.notify.daemon import storage

        server = f"test_server_{int(time.time())}.local"
        mailbox = "INBOX"

        storage.set_last_uid(pool, server, mailbox, 42)

        uid = storage.get_last_uid(pool, server, mailbox)
        assert uid == 42, f"Expected 42, got {uid}"

        storage.set_last_uid(pool, server, mailbox, 100)
        uid = storage.get_last_uid(pool, server, mailbox)
        assert uid == 100, f"Expected 100, got {uid}"

    def test_record_and_get_history(
        self, db_connection, create_test_users, pool
    ):
        """Verify record_notification() and get_notification_history() work."""
        from bbsengine6.notify.daemon import storage

        notification_type = f"test.daemon.{int(time.time())}"
        recipients = ["user1", "user2"]
        template_vars = {"key": "value"}

        record_id = storage.record_notification(
            pool,
            notification_type,
            recipients,
            template_vars,
            notification_id=1,
            status="sent",
        )
        assert record_id is not None, "record_notification returned None"

        history = storage.get_notification_history(
            pool,
            notification_type=notification_type,
            limit=10,
        )
        assert len(history) > 0, "No history returned"

        found = any(h["id"] == record_id for h in history)
        assert found, f"Record {record_id} not in history"

        assert history[0]["notification_type"] == notification_type
        assert list(history[0]["recipients"]) == recipients
        assert "data" in history[0]