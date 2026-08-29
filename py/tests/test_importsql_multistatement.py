"""
Tests for ``bbsengine6.database.importsql`` multi-statement handling.

The pre-existing failure: ``importsql`` used ``cur.execute(sql_script)``
on the raw contents of a ``.sql`` resource. psycopg3's ``Cursor.execute``
only accepts a single statement per call (the server's prepared-
statement protocol rejects multi-command strings), so loading any
multi-statement file (``bank_schema.sql``, ``bank_account.sql``,
``createrol.sql``, ``member_flag.sql``, etc.) raised

    psycopg.errors.SyntaxError: cannot insert multiple commands into a
    prepared statement

at runtime, even though every backend bootstrap module relies on
``importsql`` to load these files.

The fix: ``importsql`` now splits the loaded script into individual
statements via ``_split_sql_statements`` and issues one
``cur.execute`` per statement. These tests pin that behavior.

Coverage:

  * ``_split_sql_statements`` unit tests for the splitter itself
    (handles ``--`` / ``/* */`` comments, single- and double-quoted
    literals with escapes, dollar-quoted blocks including tagged
    variants, whitespace / comment-only scripts).
  * ``importsql`` behavior tests confirming it issues one
    ``cur.execute`` per statement, stops at the first failure,
    rolls back when ``rollback=True`` (and does not when
    ``rollback=False``), and includes the filename + a statement
    preview in the traceback log.
  * End-to-end smoke against an actual multi-statement file shipped
    with the package (``bank_schema.sql``) to prove the splitter
    handles the production content.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from bbsengine6 import database

# All tests in this module are pure unit tests: no DB connection
# required. Marking them explicitly keeps the conftest's session-level
# DB fixtures from activating when only this file is being run.
pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_args():
    """Minimal argparse args stand-in for database.* helpers."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": os.environ.get("BBSENGINE6_DBNAME", "zoid6test"),
        "databasehost": os.environ.get("BBSENGINE6_DBHOST", "localhost"),
        "databaseport": int(os.environ.get("BBSENGINE6_DBPORT", "5432")),
        "databaseuser": os.environ.get("BBSENGINE6_DBUSER", "nobody"),
        "databasepassword": os.environ.get("BBSENGINE6_DBPASSWORD"),
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


class _FakeCursor:
    """Cursor-shaped mock that records every ``execute`` call.

    Mirrors the contract ``importsql`` relies on: a context manager
    that yields a cursor whose ``execute`` can be inspected and made
    to raise on a chosen call.
    """

    def __init__(self, raise_on_call: int | None = None):
        self.calls: list[str] = []
        self._raise_on = raise_on_call
        self._idx = 0

    def execute(self, statement: str) -> None:
        self.calls.append(statement)
        if self._raise_on is not None and self._idx == self._raise_on:
            self._idx += 1
            raise psycopg.errors.SyntaxError(
                "cannot insert multiple commands into a prepared statement"
            )
        self._idx += 1

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


def _fake_cursor_factory(raise_on_call: int | None = None):
    """Build a ``database.cursor``-shaped callable returning ``_FakeCursor``.

    Returns a function suitable for ``monkeypatch.setattr(database,
    "cursor", ...)`` that ignores its arguments and hands back a fresh
    ``_FakeCursor`` instance per call. The caller can then inspect
    ``.calls`` to assert the exact sequence of statements executed.
    """

    def _factory(*_a, **_kw):
        return _FakeCursor(raise_on_call=raise_on_call)

    return _factory


def _stub_load_sql(monkeypatch, sql_text: str):
    """Patch ``util.load_sql`` so ``importsql`` reads ``sql_text``."""

    def _fake_load(_args, _filename, *, package=None):
        return sql_text

    monkeypatch.setattr(database.util, "load_sql", _fake_load)


# ---------------------------------------------------------------------------
# Splitter unit tests
# ---------------------------------------------------------------------------


class TestSplitSqlStatements:
    """Direct coverage for ``_split_sql_statements``."""

    def test_two_simple_statements(self):
        sql = "CREATE TABLE foo (id int); CREATE TABLE bar (id int);"
        out = database._split_sql_statements(sql)
        assert out == [
            "CREATE TABLE foo (id int);",
            "CREATE TABLE bar (id int);",
        ]

    def test_single_statement_no_trailing_semicolon(self):
        sql = "SELECT 1"
        out = database._split_sql_statements(sql)
        assert out == ["SELECT 1"]

    def test_single_statement_with_trailing_semicolon(self):
        sql = "SELECT 1;"
        out = database._split_sql_statements(sql)
        assert out == ["SELECT 1;"]

    def test_line_comment_with_semicolon_inside(self):
        sql = "-- this ; is not a separator\nSELECT 1;\n-- another ;\nSELECT 2;"
        out = database._split_sql_statements(sql)
        assert out == ["SELECT 1;", "SELECT 2;"]

    def test_block_comment_with_semicolon_inside(self):
        sql = "/* foo ; bar */ SELECT 1; /* baz ; qux */ SELECT 2;"
        out = database._split_sql_statements(sql)
        # Comments are stripped from the output (PostgreSQL accepts
        # them in-band, but cleaner statement strings are easier to
        # log and reason about).
        assert out == ["SELECT 1;", "SELECT 2;"]

    def test_nested_block_comment(self):
        # PostgreSQL accepts nested block comments; the splitter must too.
        sql = "/* outer /* inner ; */ still outer */ SELECT 1;"
        out = database._split_sql_statements(sql)
        assert out == ["SELECT 1;"]

    def test_single_quoted_literal_with_semicolon(self):
        sql = "INSERT INTO t VALUES ('a;b'); SELECT 1;"
        out = database._split_sql_statements(sql)
        assert out == [
            "INSERT INTO t VALUES ('a;b');",
            "SELECT 1;",
        ]

    def test_single_quoted_literal_with_escaped_quote(self):
        # '' inside a string literal must not close the literal.
        sql = "INSERT INTO t VALUES ('it''s;ok'); SELECT 1;"
        out = database._split_sql_statements(sql)
        assert out == [
            "INSERT INTO t VALUES ('it''s;ok');",
            "SELECT 1;",
        ]

    def test_double_quoted_identifier_with_semicolon(self):
        sql = 'CREATE TABLE "weird;name" (id int); SELECT 1;'
        out = database._split_sql_statements(sql)
        assert out == [
            'CREATE TABLE "weird;name" (id int);',
            "SELECT 1;",
        ]

    def test_dollar_quoted_does_not_split_inside(self):
        # The body of a $$ ... $$ block contains ; which must not split.
        sql = (
            "CREATE FUNCTION foo() RETURNS void AS $$ "
            "BEGIN ; END; "
            "$$ LANGUAGE plpgsql; "
            "grant execute on function foo() to public;"
        )
        out = database._split_sql_statements(sql)
        assert out == [
            (
                "CREATE FUNCTION foo() RETURNS void AS $$ "
                "BEGIN ; END; "
                "$$ LANGUAGE plpgsql;"
            ),
            "grant execute on function foo() to public;",
        ]

    def test_tagged_dollar_quote(self):
        sql = (
            "CREATE FUNCTION bar() RETURNS void AS $func$ "
            "BEGIN ; END $func$ "
            "LANGUAGE plpgsql; SELECT 1;"
        )
        out = database._split_sql_statements(sql)
        assert out == [
            (
                "CREATE FUNCTION bar() RETURNS void AS $func$ "
                "BEGIN ; END $func$ "
                "LANGUAGE plpgsql;"
            ),
            "SELECT 1;",
        ]

    def test_empty_script(self):
        assert database._split_sql_statements("") == []

    def test_whitespace_only_script(self):
        assert database._split_sql_statements("   \n\t  \n") == []

    def test_comment_only_script(self):
        assert database._split_sql_statements(
            "-- just a comment\n/* and */ -- another ;\n"
        ) == []

    def test_statement_separated_only_by_whitespace_is_single_statement(self):
        # The splitter is intentionally ``;``-based (not line-based):
        # PostgreSQL's prepared-statement protocol only accepts a
        # single statement per ``execute`` call, so we require an
        # explicit ``;`` terminator. Two ``SELECT`` statements
        # separated only by whitespace remain one chunk; callers
        # who want to ship such files should add ``;`` separators.
        sql = "SELECT 1\nSELECT 2\n"
        out = database._split_sql_statements(sql)
        assert out == ["SELECT 1\nSELECT 2"]

    def test_real_bank_schema_file(self):
        """End-to-end check against an actual shipped multi-statement file."""
        path = (
            Path(__file__).resolve().parents[1]
            / "src" / "bbsengine6" / "sql" / "bank_schema.sql"
        )
        assert path.exists(), f"expected {path} to exist for the smoke test"
        text = path.read_text(encoding="utf-8")
        out = database._split_sql_statements(text)
        # bank_schema.sql has 1 CREATE SCHEMA + 4 GRANT statements (6 ';'s).
        assert len(out) == 6
        assert out[0].startswith("create schema if not exists bank;")
        assert out[-1].startswith("grant create on schema bank to sysop;")


# ---------------------------------------------------------------------------
# importsql behavioral tests
# ---------------------------------------------------------------------------


class TestImportsqlExecutesPerStatement:
    """importsql must issue one ``cur.execute`` per split statement."""

    def test_two_statements_each_reach_cursor(
        self, test_args, monkeypatch
    ):
        _stub_load_sql(
            monkeypatch,
            "CREATE TABLE foo (id int); CREATE TABLE bar (id int);",
        )
        cur = _FakeCursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(test_args, "dummy.sql", conn=conn)

        assert result is True
        assert cur.calls == [
            "CREATE TABLE foo (id int);",
            "CREATE TABLE bar (id int);",
        ]

    def test_single_statement_one_execute_call(
        self, test_args, monkeypatch
    ):
        _stub_load_sql(monkeypatch, "SELECT 1;")
        cur = _FakeCursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(test_args, "dummy.sql", conn=conn)

        assert result is True
        assert cur.calls == ["SELECT 1;"]

    def test_empty_script_returns_true_with_no_executes(
        self, test_args, monkeypatch
    ):
        _stub_load_sql(monkeypatch, "")
        cur = _FakeCursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(test_args, "empty.sql", conn=conn)

        assert result is True
        assert cur.calls == []


class TestImportsqlFailureSemantics:
    """Failure-path behavior must match the existing contract."""

    def test_failure_on_second_statement_rolls_back_and_returns_false(
        self, test_args, monkeypatch
    ):
        _stub_load_sql(
            monkeypatch,
            "SELECT 1; SELECT 2; SELECT 3;",
        )
        cur = _FakeCursor(raise_on_call=1)
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(
            test_args, "dummy.sql", conn=conn, rollback=True
        )

        assert result is False
        # Statements 0 and 1 ran (statement 1 raised); statement 2
        # must NOT have been attempted.
        assert len(cur.calls) == 2
        assert conn.rollback.called

    def test_failure_with_rollback_false_does_not_rollback(
        self, test_args, monkeypatch
    ):
        _stub_load_sql(monkeypatch, "SELECT 1; SELECT 2;")
        cur = _FakeCursor(raise_on_call=0)
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(
            test_args, "dummy.sql", conn=conn, rollback=False
        )

        assert result is False
        assert not conn.rollback.called

    def test_failure_logs_filename_and_statement_preview(
        self, test_args, monkeypatch
    ):
        """The traceback log must include the filename and a preview
        of the failing statement so operators can find the bad SQL
        without rerunning with debug logging."""
        _stub_load_sql(monkeypatch, "SELECT 1; SELECT 2;")
        cur = _FakeCursor(raise_on_call=1)
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        # Capture the traceback message.
        captured: list[str] = []

        def _fake_traceback(msg, *a, **kw):
            captured.append(msg)

        monkeypatch.setattr(database.io, "echo_traceback", _fake_traceback)

        conn = MagicMock(name="conn")
        database.importsql(test_args, "boom.sql", conn=conn, rollback=False)

        assert captured, "echo_traceback must have been called"
        msg = captured[0]
        assert "boom.sql" in msg
        assert "SELECT 2" in msg
        # Preview is capped at 200 chars, but for our tiny statement
        # the whole thing fits.
        assert "::" in msg


class TestImportsqlEndToEndWithRealFile:
    """Smoke test against an actual on-disk multi-statement resource."""

    def test_bank_schema_file_executes_all_statements(
        self, test_args, monkeypatch
    ):
        # Don't stub load_sql: let it read the real file from the
        # installed package so we exercise the full code path.
        cur = _FakeCursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.importsql(test_args, "bank_schema.sql", conn=conn)

        assert result is True
        # 1 CREATE SCHEMA + 4 GRANT statements; we expect 6 execute calls.
        assert len(cur.calls) == 6
        assert cur.calls[0].startswith("create schema if not exists bank;")
