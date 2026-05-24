"""
Schema validation tests for notify tables.

Verifies that all column names used in notify_message_demo.py queries
match the actual database schema. This prevents hardcoded column names
that don't exist from causing runtime errors.

Run with: pytest py/tests/test_notify_schema_columns.py -xvs
"""

import pytest


@pytest.mark.integration
class TestNotifySchemaColumns:
    """Test that column names in code match the actual database schema."""

    def test_notify_table_columns_exist(self, db_connection):
        """Verify engine.__notify has all required columns used in queries."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify'
                ORDER BY column_name
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        required_columns = {
            "id",
            "notification_type",
            "sender_moniker",
            "template",
            "template_vars",
            "rendered_message",
            "data",
            "urgency",
            "should_persist",
            "datecreated",
            "createdbymoniker",
        }

        missing = required_columns - columns
        assert not missing, f"Missing columns in engine.__notify: {missing}"

    def test_notify_recipient_table_columns_exist(self, db_connection):
        """Verify engine.__notify_recipient has all required columns."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_recipient'
                ORDER BY column_name
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        required_columns = {
            "notify_id",
            "recipient_moniker",
            "sessionid",
            "is_blocked",
            "delivered_at",
            "read_at",
            "datecreated",
        }

        missing = required_columns - columns
        assert not missing, f"Missing columns in engine.__notify_recipient: {missing}"

    def test_notify_recipient_has_no_id_column(self, db_connection):
        """Verify engine.__notify_recipient does NOT have an 'id' column.

        The composite primary key is (notify_id, recipient_moniker).
        """
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_recipient'
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        assert "id" not in columns, (
            "engine.__notify_recipient should not have 'id' column - "
            "it uses composite primary key (notify_id, recipient_moniker)"
        )

    def test_notify_recipient_has_no_is_read_column(self, db_connection):
        """Verify engine.__notify_recipient does NOT have 'is_read' column.

        Read status is tracked via read_at timestamp, not a boolean.
        """
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_recipient'
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        assert "is_read" not in columns, (
            "engine.__notify_recipient should not have 'is_read' column - "
            "use read_at timestamp instead"
        )

    def test_notify_table_has_no_created_at_column(self, db_connection):
        """Verify engine.__notify does NOT have 'created_at' column.

        Timestamps use 'datecreated', not 'created_at'.
        """
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify'
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        assert "created_at" not in columns, (
            "engine.__notify should not have 'created_at' column - "
            "use 'datecreated' instead"
        )

    def test_notify_select_query_works(self, db_connection, create_test_users):
        """Verify SELECT with datecreated works (not created_at)."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT id, sender_moniker, rendered_message, datecreated
                FROM engine.__notify
                ORDER BY datecreated DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is None or len(row) == 4, "Query should return 4 columns"

    def test_notify_recipient_select_query_works(self, db_connection, create_test_users):
        """Verify SELECT using read_at (not is_read) works."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT nr.notify_id, nr.recipient_moniker, nr.read_at
                FROM engine.__notify_recipient nr
                WHERE nr.read_at IS NULL
                LIMIT 1
                """
            )
            row = cur.fetchone()

        assert row is None or len(row) == 3, "Query should return 3 columns"

    def test_notify_recipient_join_query_works(self, db_connection, create_test_users):
        """Verify JOIN between __notify and __notify_recipient works."""
        import getpass

        user = getpass.getuser()
        test_moniker = f"test_{user}_1"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT n.id, n.sender_moniker, n.rendered_message, n.datecreated
                FROM engine.__notify n
                JOIN engine.__notify_recipient nr ON n.id = nr.notify_id
                WHERE nr.recipient_moniker = %s AND nr.read_at IS NULL
                ORDER BY n.datecreated DESC
                LIMIT 1
                """,
                (test_moniker,),
            )
            row = cur.fetchone()

        assert row is None or len(row) == 4, "Join query should return 4 columns"

    def test_mark_messages_read_uses_correct_columns(self, db_connection, create_test_users):
        """Verify UPDATE using read_at works (not is_read)."""
        import getpass

        user = getpass.getuser()
        test_moniker = f"test_{user}_1"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                UPDATE engine.__notify_recipient
                SET read_at = now()
                WHERE recipient_moniker = %s AND read_at IS NULL
                RETURNING notify_id
                """,
                (test_moniker,),
            )
            cur.fetchall()

        db_connection.rollback()