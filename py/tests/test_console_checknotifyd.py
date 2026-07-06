"""
Integration tests for console checknotifyd module.

Tests that the notifyd tables (engine.__notify_imap_state and
engine.__notify_history) exist in the database and have the correct schema.

Run with: pytest py/tests/test_console_checknotifyd.py -xvs
"""

import pytest
from pathlib import Path


@pytest.mark.integration
class TestNotifydSchema:
    """Verify notifyd tables exist with correct structure."""

    def test_imap_state_table_exists(self, db_connection):
        """Verify engine.__notify_imap_state exists."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'engine'
                    AND table_name = '__notify_imap_state'
                )
                """
            )
            assert cur.fetchone()[0] is True, "engine.__notify_imap_state not found"

    def test_history_table_exists(self, db_connection):
        """Verify engine.__notify_history exists."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'engine'
                    AND table_name = '__notify_history'
                )
                """
            )
            assert cur.fetchone()[0] is True, "engine.__notify_history not found"

    def test_imap_state_columns(self, db_connection):
        """Verify engine.__notify_imap_state has all required columns."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_imap_state'
                ORDER BY column_name
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        required = {"id", "server", "mailbox", "max_uid", "last_checked", "dateupdated"}
        missing = required - columns
        assert not missing, f"Missing columns in __notify_imap_state: {missing}"

    def test_imap_state_unique_constraint(self, db_connection):
        """Verify engine.__notify_imap_state has UNIQUE(server, mailbox)."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM information_schema.table_constraints
                WHERE table_schema = 'engine'
                AND table_name = '__notify_imap_state'
                AND constraint_type = 'UNIQUE'
                AND constraint_name LIKE '%server%'
                LIMIT 1
                """
            )
            assert cur.fetchone() is not None, (
                "UNIQUE constraint on server/mailbox not found"
            )

    def test_imap_state_server_index(self, db_connection):
        """Verify index exists on (server, mailbox)."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'engine'
                AND tablename = '__notify_imap_state'
                AND indexname LIKE '%%server%%'
                LIMIT 1
                """
            )
            assert cur.fetchone() is not None, "Index on server column not found"

    def test_history_columns(self, db_connection):
        """Verify engine.__notify_history has all required columns."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'engine'
                AND table_name = '__notify_history'
                ORDER BY column_name
                """
            )
            columns = {row[0] for row in cur.fetchall()}

        required = {
            "id",
            "notification_type",
            "recipients",
            "datesent",
            "notification_id",
            "data",
            "status",
            "error_message",
        }
        missing = required - columns
        assert not missing, f"Missing columns in __notify_history: {missing}"

    def test_history_has_indices(self, db_connection):
        """Verify __notify_history has at least one index (primary key)."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'engine'
                AND tablename = '__notify_history'
                """
            )
            indices = {row[0] for row in cur.fetchall()}

        assert len(indices) > 0, (
            "Expected at least primary key index on __notify_history"
        )


@pytest.mark.integration
class TestNotifydSQLFile:
    """Verify the notifyd.sql file exists and contains expected content."""

    def test_notifyd_sql_exists(self):
        """Verify sql/notifyd.sql exists."""
        sql_path = (
            Path(__file__).parent.parent / "src" / "bbsengine6" / "sql" / "notifyd.sql"
        )
        assert sql_path.exists(), f"notifyd.sql not found at {sql_path}"

    def test_notifyd_sql_creates_imap_state(self):
        """Verify notifyd.sql contains engine.__notify_imap_state CREATE TABLE."""
        sql_path = (
            Path(__file__).parent.parent / "src" / "bbsengine6" / "sql" / "notifyd.sql"
        )
        content = sql_path.read_text()
        assert "engine.__notify_imap_state" in content
        assert "CREATE TABLE" in content or "CREATE TABLE IF NOT EXISTS" in content

    def test_notifyd_sql_creates_history(self):
        """Verify notifyd.sql contains engine.__notify_history CREATE TABLE."""
        sql_path = (
            Path(__file__).parent.parent / "src" / "bbsengine6" / "sql" / "notifyd.sql"
        )
        content = sql_path.read_text()
        assert "engine.__notify_history" in content
        assert "CREATE TABLE" in content or "CREATE TABLE IF NOT EXISTS" in content

    def test_notifyd_sql_has_grants(self):
        """Verify notifyd.sql grants permissions to web, sysop, term."""
        sql_path = (
            Path(__file__).parent.parent / "src" / "bbsengine6" / "sql" / "notifyd.sql"
        )
        content = sql_path.read_text()
        assert "GRANT" in content
        assert "web" in content
        assert "sysop" in content
        assert "term" in content


@pytest.mark.integration
class TestNotifydModuleFunctions:
    """Test the checknotifyd module's init, buildargs, access, main functions.

    The console shim was removed in 2026-07-06: ``console checknotifyd``
    now dispatches to ``bbsengine6.backend.checknotifyd``. These tests
    exercise the backend module directly. Note: ``access()`` now
    requires sysop privilege via the connection (see
    ``bbsengine6.backend.lib.issysop``), so calling it without
    ``conn``/``pool`` returns False.
    """

    def test_module_can_be_imported(self):
        """Verify bbsengine6.backend.checknotifyd imports without error."""
        from bbsengine6.backend import checknotifyd  # noqa: F401

    def test_init_returns_true(self):
        """Verify init() returns True."""
        from bbsengine6.backend import checknotifyd

        result = checknotifyd.init(None)
        assert result is True

    def test_buildargs_returns_parser(self):
        """Verify buildargs() returns an ArgumentParser (or None)."""
        from bbsengine6.backend import checknotifyd

        parser = checknotifyd.buildargs(None)
        # backend.lib.buildargs may return None when no parent parser is
        # provided; accept either an ArgumentParser or None.
        assert parser is None or hasattr(parser, "parse_args")

    def test_access_returns_false_without_conn(self):
        """Verify access() requires a conn/pool and returns False otherwise."""
        from bbsengine6.backend import checknotifyd

        # No conn/pool -> issysop() fails -> access() returns False.
        result = checknotifyd.access(None, "read")
        assert result is False


@pytest.mark.integration
class TestNotifydStorageQueries:
    """Test that storage.py queries work against the created tables."""

    def test_imap_state_insert_and_select(self, db_connection):
        """Verify we can INSERT and SELECT from engine.__notify_imap_state."""
        server = "test.example.com"
        mailbox = "INBOX"

        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__notify_imap_state (server, mailbox, max_uid)
                VALUES (%s, %s, 42)
                ON CONFLICT (server, mailbox)
                DO UPDATE SET max_uid = 42, dateupdated = CURRENT_TIMESTAMP
                RETURNING max_uid
                """,
                (server, mailbox),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == 42

            cur.execute(
                """
                SELECT server, mailbox, max_uid
                FROM engine.__notify_imap_state
                WHERE server = %s AND mailbox = %s
                """,
                (server, mailbox),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == server
            assert row[1] == mailbox
            assert row[2] == 42

    def test_history_insert_and_select(self, db_connection):
        """Verify we can INSERT and SELECT from engine.__notify_history."""
        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__notify_history
                (notification_type, recipients, status)
                VALUES ('test.type', ARRAY['alice', 'bob'], 'sent')
                RETURNING id, notification_type, status
                """,
            )
            row = cur.fetchone()
            assert row is not None
            record_id = row[0]
            assert row[1] == "test.type"
            assert row[2] == "sent"

            cur.execute(
                """
                SELECT id, notification_type, recipients, status
                FROM engine.__notify_history
                WHERE id = %s
                """,
                (record_id,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == record_id
            assert row[1] == "test.type"
            assert list(row[2]) == ["alice", "bob"]
            assert row[3] == "sent"

    def test_history_with_jsonb_data(self, db_connection):
        """Verify engine.__notify_history supports JSONB data column."""
        import json

        test_data = {"key": "value", "nested": {"a": 1}}
        json_str = json.dumps(test_data)

        with db_connection.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine.__notify_history
                (notification_type, recipients, data, status, error_message)
                VALUES ('test.json', ARRAY['alice'], %s::jsonb, 'sent', NULL)
                RETURNING id, data
                """,
                (json_str,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[1] is not None

            cur.execute(
                """
                SELECT data FROM engine.__notify_history WHERE id = %s
                """,
                (row[0],),
            )
            stored = cur.fetchone()
            assert stored is not None
            assert stored[0] == test_data
