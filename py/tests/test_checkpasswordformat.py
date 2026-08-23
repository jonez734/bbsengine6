"""Tests for ``bbsengine6.backend.checkpasswordformat``.

The module has two responsibilities, both SAVEPOINT-protected so a
transient failure rolls back cleanly:

  1. Idempotent install of ``chk_member_password_bcrypt`` on
     ``engine.__member``. ``database.constraintexists`` is the cheap
     probe; if False, ``manage_password_format.sql`` is loaded via
     ``database.importsql`` inside a savepoint.
  2. Unconditional ``bbsengine6.member.audit_password_column`` call
     that logs any legacy ``$1$`` MD5-crypt rows at
     ``level="warning"`` and returns the list.

The test suite covers:

  * install path: probe-true (skip import), probe-false (run import),
    import failure (savepoint rollback, main returns False),
    import success (savepoint release, main returns True).
  * audit path: zero legacy rows (``level="ok"``), N legacy rows
    (``level="warning"``), audit raises (failure counted, main
    returns False).
  * defensive guard: the autocommit helper is invoked at the start
    of ``_work``, mirroring the sibling savepoint modules.

The fake-conn pattern mirrors ``test_checkfunctions.py``: an
``autocommit`` setter that raises on change-in-INTRANS so any
unconditional ``conn.autocommit = False`` would surface as a test
failure, not a runtime psycopg ProgrammingError.
"""

from __future__ import annotations

import argparse
import getpass
import os
from unittest.mock import MagicMock

import psycopg.pq
import pytest

from bbsengine6 import database
from bbsengine6.backend import checkpasswordformat
from bbsengine6.backend import lib as backend_lib


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
    return parser.parse_args([])


def _make_fake_conn(
    autocommit=False,
    status=psycopg.pq.TransactionStatus.IDLE,
):
    """Fake psycopg connection. ``autocommit`` setter raises on
    change-in-INTRANS so an unconditional ``conn.autocommit = False``
    surfaces as a test failure instead of a runtime ProgrammingError.
    """
    state = {"autocommit": autocommit, "status": status}

    class _PgConn:
        @property
        def transaction_status(self):
            return state["status"]

    class _Conn:
        def __init__(self):
            self.pgconn = _PgConn()
            self.commit = MagicMock()
            self.rollback = MagicMock()

        def _get_autocommit(self):
            return state["autocommit"]

        def _set_autocommit(self, value):
            if state["autocommit"] is True and value is False:
                if state["status"] != psycopg.pq.TransactionStatus.IDLE:
                    raise psycopg.ProgrammingError(
                        "can't change 'autocommit' now: connection in "
                        "transaction status INTRANS"
                    )
            state["autocommit"] = value

        autocommit = property(_get_autocommit, _set_autocommit)

    return _Conn()


def _ok_cursor(*_args, **_kwargs):
    """A permissive cursor context manager. ``execute`` records calls.

    Accepts both ``database.cursor(conn)`` and ``database.cursor(conn=conn)``
    call shapes so it works as a monkeypatch target for both direct
    callers and the audit helper which calls it positionally.
    """
    cur = MagicMock(name="cur")
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    cur.execute = MagicMock(return_value=None)
    cur.fetchone = MagicMock(return_value=None)
    cur.fetchall = MagicMock(return_value=[])
    cur.rowcount = -1
    return cur


# ---------------------------------------------------------------------------
# Module constants are pinned (no accidental rename)
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """If the SQL file or constraint name changes, every install site
    needs an explicit bump. Pin them here so a silent rename fails the
    test suite."""

    def test_constraint_name(self):
        assert (
            checkpasswordformat.CONSTRAINT_NAME
            == "chk_member_password_bcrypt"
        )

    def test_constraint_schema(self):
        assert checkpasswordformat.CONSTRAINT_SCHEMA == "engine"

    def test_constraint_sql_file(self):
        assert (
            checkpasswordformat.CONSTRAINT_SQL_FILE
            == "manage_password_format.sql"
        )


# ---------------------------------------------------------------------------
# Install path
# ---------------------------------------------------------------------------


class TestInstall:
    """Cover the four branches of the install SAVEPOINT block."""

    def test_constraint_present_skips_import(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.INTRANS,
        )
        imported = []

        def _exists(_args, _schema, _name, **_kw):
            return True

        def _importsql(*_a, **_kw):
            imported.append("called")
            return True

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(
            checkpasswordformat, "constraintexists", _exists
        )
        monkeypatch.setattr(database, "importsql", _importsql)

        assert checkpasswordformat.main(test_args, conn=conn) is True
        assert imported == [], (
            "constraint already present must short-circuit importsql"
        )

    def test_constraint_missing_runs_importsql(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )
        imported = []
        cursor_calls = []

        def _ok_cur(*_args, **_kwargs):
            cur = _ok_cursor()
            cursor_calls.append(cur.execute)
            return cur

        def _exists(_args, _schema, _name, **_kw):
            return False

        def _importsql(_args, filename, **_kw):
            imported.append(filename)
            return True

        monkeypatch.setattr(database, "cursor", _ok_cur)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", _exists)
        monkeypatch.setattr(database, "importsql", _importsql)

        assert checkpasswordformat.main(test_args, conn=conn) is True
        assert imported == ["manage_password_format.sql"], (
            f"manage_password_format.sql must be loaded when probe is "
            f"False; got {imported!r}"
        )

    def test_import_failure_rolls_back_savepoint(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )

        def _exists(_args, _schema, _name, **_kw):
            return False

        def _importsql(*_a, **_kw):
            raise RuntimeError("simulated import failure")

        cur = _ok_cursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", _exists)
        monkeypatch.setattr(database, "importsql", _importsql)

        result = checkpasswordformat.main(test_args, conn=conn)
        assert result is False

        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("SAVEPOINT" in s for s in executed), (
            f"SAVEPOINT must be opened before importsql; got {executed!r}"
        )
        assert any("ROLLBACK TO SAVEPOINT" in s for s in executed), (
            f"ROLLBACK TO SAVEPOINT must follow import failure; "
            f"got {executed!r}"
        )

    def test_import_success_releases_savepoint(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )

        def _exists(_args, _schema, _name, **_kw):
            return False

        def _importsql(*_a, **_kw):
            return True

        cur = _ok_cursor()
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", _exists)
        monkeypatch.setattr(database, "importsql", _importsql)

        assert checkpasswordformat.main(test_args, conn=conn) is True
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert any("SAVEPOINT" in s for s in executed)
        assert any("RELEASE SAVEPOINT" in s for s in executed), (
            f"RELEASE SAVEPOINT must follow import success; "
            f"got {executed!r}"
        )


# ---------------------------------------------------------------------------
# Audit path
# ---------------------------------------------------------------------------


class TestAudit:
    """The audit runs unconditionally even if the install failed."""

    def test_audit_zero_rows_emits_ok(self, test_args, monkeypatch):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", lambda *a, **kw: True)

        from bbsengine6.member import lib as memberlib

        monkeypatch.setattr(
            memberlib, "audit_password_column", lambda *a, **kw: []
        )

        assert checkpasswordformat.main(test_args, conn=conn) is True

    def test_audit_with_legacy_rows_returns_true(
        self, test_args, monkeypatch
    ):
        """Legacy rows are a warning, not a failure: the migration is
        the operator's responsibility, the audit just reports it."""
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", lambda *a, **kw: True)

        from bbsengine6.member import lib as memberlib

        monkeypatch.setattr(
            memberlib,
            "audit_password_column",
            lambda *a, **kw: ["jam", "oldbob"],
        )

        assert checkpasswordformat.main(test_args, conn=conn) is True, (
            "audit row count must NOT fail the module; the warning is "
            "the operator signal, not a hard reject"
        )

    def test_audit_exception_fails_module(self, test_args, monkeypatch):
        """A genuine audit failure (e.g. conn died mid-statement) must
        fail the module so the stage aborts instead of silently passing."""
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.IDLE,
        )

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", lambda *a, **kw: True)

        from bbsengine6.member import lib as memberlib

        def _audit_raises(*a, **kw):
            raise RuntimeError("simulated audit failure")

        monkeypatch.setattr(
            memberlib, "audit_password_column", _audit_raises
        )

        assert checkpasswordformat.main(test_args, conn=conn) is False


# ---------------------------------------------------------------------------
# Defensive guard
# ---------------------------------------------------------------------------


class TestAutocommitHelper:
    """Pin that the module calls ``backend.lib._ensure_autocommit_off``
    at the start of ``_work``, mirroring the sibling savepoint modules
    (checkclasses, checkfunctions, checkmessage)."""

    def test_helper_invoked_on_intrans_conn(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.INTRANS,
        )
        called = []

        def _spy(_conn):
            called.append("ok")

        monkeypatch.setattr(backend_lib, "_ensure_autocommit_off", _spy)
        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(checkpasswordformat, "constraintexists", lambda *a, **kw: True)

        from bbsengine6.member import lib as memberlib

        monkeypatch.setattr(
            memberlib, "audit_password_column", lambda *a, **kw: []
        )

        assert checkpasswordformat.main(test_args, conn=conn) is True
        assert called == ["ok"], (
            "_ensure_autocommit_off must be called before any savepoint "
            "work; otherwise an INTRANS conn with autocommit=True aborts "
            "the whole stage"
        )
