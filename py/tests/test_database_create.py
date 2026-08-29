"""Tests for bbsengine6.database.exists() and bbsengine6.database.create()."""

from __future__ import annotations

import argparse
import getpass
import os
from unittest.mock import MagicMock, patch

import psycopg
import pytest

from bbsengine6 import database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_args():
    """Lightweight args namespace for tests that don't need the full conftest."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": os.environ.get("BBSENGINE6_DBNAME", "zoid6test"),
        "databasehost": os.environ.get("BBSENGINE6_DBHOST", "localhost"),
        "databaseport": int(os.environ.get("BBSENGINE6_DBPORT", "5432")),
        "databaseuser": os.environ.get("BBSENGINE6_DBUSER", getpass.getuser()),
        "databasepassword": os.environ.get("BBSENGINE6_DBPASSWORD"),
    }
    database.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])
    return args


def _make_fake_cursor():
    """Build a fake cursor that records execute() calls and returns a result.

    The cursor is also a context manager that returns itself from __enter__,
    matching psycopg's real Cursor behavior. This is required because
    ``database.cursor()`` is used in ``with`` blocks throughout the codebase.
    """
    cur = MagicMock(name="cursor")
    cur.fetchone = MagicMock(return_value=None)
    cur.fetchall = MagicMock(return_value=[])
    cur.fetchmany = MagicMock(return_value=[])
    cur.rowcount = 0
    cur.execute = MagicMock(return_value=None)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    return cur


def _make_fake_conn(cur=None, autocommit=False, with_commit=False):
    """Build a fake psycopg connection that behaves like a real one for DDL."""
    if cur is None:
        cur = _make_fake_cursor()
    conn = MagicMock(name="conn")
    conn.autocommit = autocommit
    conn.cursor = MagicMock(return_value=cur)
    if with_commit:
        conn.commit = MagicMock()
    else:
        conn.commit = MagicMock(side_effect=AssertionError("commit should not be called"))
    conn.rollback = MagicMock()
    return conn


# ---------------------------------------------------------------------------
# exists() tests
# ---------------------------------------------------------------------------


class TestExists:
    """Coverage for database.exists()."""

    def test_returns_true_when_database_exists(self, test_args):
        cur = _make_fake_cursor()
        cur.fetchone = MagicMock(return_value=(1,))
        conn = _make_fake_conn(cur=cur)

        result = database.exists(test_args, "my_db", conn=conn)
        assert result is True

    def test_returns_false_when_database_missing(self, test_args):
        cur = _make_fake_cursor()
        cur.fetchone = MagicMock(return_value=None)
        conn = _make_fake_conn(cur=cur)

        result = database.exists(
            test_args, "zoid6test_definitely_not_a_real_db", conn=conn
        )
        assert result is False

    def test_is_case_insensitive(self, test_args):
        # The case-insensitivity contract lives in the SQL composition
        # (``lower(datname) = lower(%s)``) rather than in the cluster lookup,
        # so we can verify it without a real PostgreSQL cluster.
        cur = _make_fake_cursor()
        cur.fetchone = MagicMock(return_value=(1,))
        conn = _make_fake_conn(cur=cur)

        assert database.exists(test_args, "zoid6test", conn=conn) is True
        assert database.exists(test_args, "ZOID6TEST", conn=conn) is True
        assert database.exists(test_args, "Zoid6Test", conn=conn) is True

        (stmt, _params) = cur.execute.call_args[0]
        assert "lower(datname) = lower(%s)" in stmt

    def test_no_conn_no_pool_returns_false(self, test_args):
        # No conn, no pool -> log error, return False.
        result = database.exists(test_args, "zoid6test")
        assert result is False

    def test_with_caller_conn(self, test_args):
        # Caller-supplied conn path: exists() must use the supplied conn and
        # return True when the lookup row is present.
        cur = _make_fake_cursor()
        cur.fetchone = MagicMock(return_value=(1,))
        conn = _make_fake_conn(cur=cur)

        result = database.exists(test_args, "my_db", conn=conn)
        assert result is True
        cur.execute.assert_called_once()

    def test_db_error_returns_false(self, test_args):
        # If the cursor raises a DatabaseError, exists() must return False
        # and not propagate.
        cur = _make_fake_cursor()
        cur.execute = MagicMock(side_effect=psycopg.DatabaseError("boom"))
        conn = _make_fake_conn(cur=cur)

        result = database.exists(test_args, "anything", conn=conn)
        assert result is False


# ---------------------------------------------------------------------------
# create() tests (mocked DDL — the test user lacks CREATEDB privilege)
# ---------------------------------------------------------------------------


class TestCreate:
    """Coverage for database.create()."""

    def test_emits_create_database_with_identifier(self, test_args):
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        result = database.create(test_args, "my_new_db", conn=conn)

        assert result is True
        cur.execute.assert_called_once()
        # CREATE DATABASE has no parameters, so execute() is called with
        # just the SQL statement.
        (stmt,) = cur.execute.call_args[0]
        rendered = stmt.as_string(None)
        assert "CREATE DATABASE" in rendered
        assert '"my_new_db"' in rendered

    def test_emits_owner_and_encoding_when_supplied(self, test_args):
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        result = database.create(
            test_args,
            "my_new_db",
            owner="postgres",
            encoding="UTF8",
            conn=conn,
        )

        assert result is True
        (stmt,) = cur.execute.call_args[0]
        rendered = stmt.as_string(None)  # type: ignore[arg-type]
        assert "CREATE DATABASE" in rendered
        assert '"my_new_db"' in rendered
        assert "WITH" in rendered
        assert 'OWNER = "postgres"' in rendered
        assert "ENCODING = 'UTF8'" in rendered

    def test_emits_only_options_provided(self, test_args):
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        result = database.create(
            test_args, "my_new_db", template="template0", conn=conn
        )

        assert result is True
        (stmt,) = cur.execute.call_args[0]
        rendered = stmt.as_string(None)  # type: ignore[arg-type]
        assert "TEMPLATE" in rendered
        assert "OWNER" not in rendered
        assert "ENCODING" not in rendered
        # WITH is only emitted when at least one option is present.
        assert "WITH" in rendered

    def test_no_options_omits_with_keyword(self, test_args):
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        database.create(test_args, "bare_db", conn=conn)

        (stmt,) = cur.execute.call_args[0]
        rendered = stmt.as_string(None)  # type: ignore[arg-type]
        assert "WITH" not in rendered
        assert "CREATE DATABASE" in rendered
        assert '"bare_db"' in rendered

    def test_duplicate_database_returns_false(self, test_args):
        # Simulate psycopg's DuplicateDatabase being raised on the second
        # CREATE DATABASE call for the same name.
        cur = _make_fake_cursor()
        cur.execute = MagicMock(
            side_effect=psycopg.errors.DuplicateDatabase("already exists")
        )
        conn = _make_fake_conn(cur=cur, autocommit=True)

        result = database.create(test_args, "existing_db", conn=conn)
        assert result is False

    def test_other_db_error_returns_false(self, test_args):
        cur = _make_fake_cursor()
        cur.execute = MagicMock(
            side_effect=psycopg.errors.InsufficientPrivilege(
                "permission denied to create database"
            )
        )
        conn = _make_fake_conn(cur=cur, autocommit=True)

        result = database.create(test_args, "my_new_db", conn=conn)
        assert result is False

    def test_no_conn_no_pool_returns_false(self, test_args):
        result = database.create(test_args, "my_new_db")
        assert result is False

    def test_pool_path_restores_autocommit(self, test_args):
        # When a pool is supplied, create() should:
        #  1. flip autocommit to True,
        #  2. execute the DDL,
        #  3. restore the previous autocommit value.
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=False)

        pool = MagicMock(name="pool")

        # Patch connect() to yield our fake conn (a context manager).
        @patch.object(database, "connect")
        def run(mock_connect):
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=conn)
            cm.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = cm

            result = database.create(test_args, "pool_db", pool=pool)
            assert result is True

        run()

        # After the call, autocommit should be back to False.
        assert conn.autocommit is False
        cur.execute.assert_called_once()

    def test_pool_path_restores_previous_true(self, test_args):
        # If autocommit was already True, it should remain True after the
        # call (no spurious flip to False).
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        pool = MagicMock(name="pool")

        @patch.object(database, "connect")
        def run(mock_connect):
            cm = MagicMock()
            cm.__enter__ = MagicMock(return_value=conn)
            cm.__exit__ = MagicMock(return_value=False)
            mock_connect.return_value = cm

            result = database.create(test_args, "pool_db", pool=pool)
            assert result is True

        run()

        assert conn.autocommit is True
        cur.execute.assert_called_once()

    def test_debug_log_runs_only_when_debug_true(self, test_args):
        cur = _make_fake_cursor()
        conn = _make_fake_conn(cur=cur, autocommit=True)

        debug_args = argparse.Namespace(debug=True)
        result = database.create(debug_args, "logged_db", conn=conn)
        assert result is True
        # No assertion on io.echo side effects here; the key point is that
        # the function does not raise when args.debug is True and that the
        # SQL composition path stays stable.

    def test_caller_conn_autocommit_false_raises_server_error_caught(
        self, test_args
    ):
        # When the caller passes a non-autocommit conn, the server rejects
        # CREATE DATABASE with "cannot run inside a transaction block".
        # Our function must catch and return False rather than propagate.
        cur = _make_fake_cursor()
        cur.execute = MagicMock(
            side_effect=psycopg.errors.ActiveSqlTransaction(
                "CREATE DATABASE cannot run inside a transaction block"
            )
        )
        conn = _make_fake_conn(cur=cur, autocommit=False)

        result = database.create(test_args, "my_new_db", conn=conn)
        assert result is False
