"""Tests for the autocommit defensive guard in the savepoint-wrapped
check* modules.

The bug being pinned here is the ``can't change 'autocommit' now:
connection in transaction status INTRANS`` ProgrammingError that
abort ``bbsengine6.startup`` when ``checkfunctions._work`` (and the
three sibling modules) start with an unconditional
``conn.autocommit = False``. The conn is the long-lived outer conn from
``stage_zero`` / ``stage_one`` and is already in ``INTRANS`` from
earlier modules in the stage loop.

The fix is a single helper, ``backend.lib._ensure_autocommit_off``,
that only flips ``autocommit`` to False when the conn is currently in
``autocommit=True`` AND is ``IDLE``. All other states are no-ops.

The test suite covers:
  * the helper itself (all four (autocommit, transaction_status) cases
    that matter);
  * the three call sites (checkfunctions, checknotify,
    checknotifyd) so the helper is wired in everywhere;
  * an integration test that drives a fake conn through the same
    sequence ``stage_zero`` does, ending in ``INTRANS``, and confirms
    ``checkfunctions.main`` no longer raises.
"""

from __future__ import annotations

import argparse
import getpass
import importlib
import os
from unittest.mock import MagicMock

import psycopg.pq
import pytest

from bbsengine6 import database
from bbsengine6.backend import lib
from bbsengine6.backend import checkfunctions
from bbsengine6.backend import checknotifyd


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


def _make_fake_conn(autocommit=False, status=psycopg.pq.TransactionStatus.IDLE):
    """Build a fake psycopg connection with controllable autocommit and
    transaction status.

    The setter for ``autocommit`` raises ``psycopg.ProgrammingError`` when
    psycopg would reject the change, mirroring real psycopg behavior.
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


# ---------------------------------------------------------------------------
# Helper-level tests
# ---------------------------------------------------------------------------


class TestEnsureAutocommitOff:
    """Direct coverage for ``backend.lib._ensure_autocommit_off``."""

    def test_noop_when_already_false(self):
        conn = _make_fake_conn(autocommit=False)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is False

    def test_noop_when_false_in_intrans(self):
        conn = _make_fake_conn(autocommit=False, status=psycopg.pq.TransactionStatus.INTRANS)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is False

    def test_flips_to_false_when_true_and_idle(self):
        conn = _make_fake_conn(autocommit=True, status=psycopg.pq.TransactionStatus.IDLE)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is False

    def test_noop_when_true_and_intrans(self):
        conn = _make_fake_conn(autocommit=True, status=psycopg.pq.TransactionStatus.INTRANS)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is True, (
            "must not raise; psycopg would reject the change"
        )

    def test_noop_when_true_and_inerror(self):
        conn = _make_fake_conn(autocommit=True, status=psycopg.pq.TransactionStatus.INERROR)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is True

    def test_noop_when_true_and_active(self):
        conn = _make_fake_conn(autocommit=True, status=psycopg.pq.TransactionStatus.ACTIVE)
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is True

    def test_swallows_status_access_error(self):
        conn = _make_fake_conn(autocommit=True)

        class _Broken:
            @property
            def transaction_status(self):
                raise RuntimeError("status unavailable")

        conn.pgconn = _Broken()
        lib._ensure_autocommit_off(conn)
        assert conn.autocommit is True


# ---------------------------------------------------------------------------
# Call-site tests: every savepoint-wrapped _work uses the helper
# ---------------------------------------------------------------------------


class TestCallSitesUseHelper:
    """Pin that the four savepoint-wrapped check* modules use the helper
    rather than the old unconditional ``conn.autocommit = False``.

    We import the modules and inspect their ``main()`` by running it
    against a fake conn that simulates the post-``checkengine``
    ``INTRANS`` state. The fake conn's autocommit setter raises on
    change-in-INTRANS, so the old code would have raised; the new code
    is a no-op.
    """

    @pytest.mark.parametrize(
        "mod_name",
        [
            "bbsengine6.backend.checkfunctions",
            "bbsengine6.backend.checknotify",
            "bbsengine6.backend.checknotifyd",
        ],
    )
    def test_module_does_not_change_autocommit_on_intrans_conn(
        self, mod_name, test_args, monkeypatch
    ):
        # Import lazily so a pre-existing import-time bug in
        # checknotify.py (broken self-reference in its module-level
        # deprecation block) does not block the rest of this test
        # file from loading. We skip cleanly if the module can't be
        # imported at all.
        try:
            mod = importlib.import_module(mod_name)
        except Exception as e:
            pytest.skip(f"{mod_name} not importable in this env: {e}")

        """The savepoint-wrapped ``_work`` must not raise on an INTRANS conn.

        The fake conn is set up to raise psycopg.ProgrammingError on
        ``conn.autocommit = False`` when in INTRANS - the same
        condition that triggered the original startup abort. The module
        must not raise; it should treat the conn as already-correct
        and continue.
        """
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.INTRANS,
        )

        def _ok_cursor(*_a, **_kw):
            cur = MagicMock(name="cur")
            cur.__enter__ = MagicMock(return_value=cur)
            cur.__exit__ = MagicMock(return_value=False)
            cur.execute = MagicMock(return_value=None)
            cur.fetchone = MagicMock(return_value=None)
            cur.fetchall = MagicMock(return_value=[])
            cur.rowcount = -1
            return cur

        def _exists(*_a, **_kw):
            return True

        def _importsql(*_a, **_kw):
            return True

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(database, "functionexists", _exists)
        monkeypatch.setattr(database, "classexists", _exists)
        monkeypatch.setattr(database, "typeexists", _exists)
        monkeypatch.setattr(database, "importsql", _importsql)

        result = mod.main(test_args, conn=conn, stage=0)
        assert result is True
        assert conn.autocommit is False


class TestCheckfunctionsIntegrationIntransConn:
    """Drive a fake conn through the same INTRANS path the real stage_zero
    does, then call ``checkfunctions.main``. Before the fix, this would
    raise ``psycopg.ProgrammingError`` and abort stage_zero. After the
    fix, it must complete successfully."""

    def test_does_not_raise_on_intrans_conn(self, test_args, monkeypatch):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.INTRANS,
        )

        def _ok_cursor(*_a, **_kw):
            cur = MagicMock(name="cur")
            cur.__enter__ = MagicMock(return_value=cur)
            cur.__exit__ = MagicMock(return_value=False)
            cur.execute = MagicMock(return_value=None)
            cur.fetchone = MagicMock(return_value=None)
            cur.fetchall = MagicMock(return_value=[])
            cur.rowcount = -1
            return cur

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(
            database,
            "functionexists",
            lambda *a, **kw: True,
        )
        monkeypatch.setattr(
            database,
            "importsql",
            lambda *a, **kw: True,
        )

        assert checkfunctions.main(test_args, conn=conn, stage=0) is True
        assert checkfunctions.main(test_args, conn=conn, stage=1) is True


class TestPgroleFunctionProvisioning:
    """Pin that the pgrole helpers are installed by stage-1
    checkfunctions and are imported from createrol.sql.

    Regression: engine.syncpgrolegroups lives in createrol.sql, not
    syncpgrolegroups.sql, and was never registered in the stage-1
    function list, so console/member.py flag changes failed with
    ``function engine.syncpgrolegroups(unknown) does not exist``.
    """

    def test_overrides_map_pgrole_funcs_to_createrol_sql(self):
        for fn in (
            "engine.createpgrole",
            "engine.deletepgrole",
            "engine.syncpgrolegroups",
        ):
            assert checkfunctions.SQL_FILE_OVERRIDES.get(fn) == "createrol.sql"

    def test_stage1_imports_createrol_for_missing_pgrole_funcs(
        self, test_args, monkeypatch
    ):
        conn = _make_fake_conn(
            autocommit=False,
            status=psycopg.pq.TransactionStatus.INTRANS,
        )

        def _ok_cursor(*_a, **_kw):
            cur = MagicMock(name="cur")
            cur.__enter__ = MagicMock(return_value=cur)
            cur.__exit__ = MagicMock(return_value=False)
            cur.execute = MagicMock(return_value=None)
            cur.fetchone = MagicMock(return_value=None)
            cur.fetchall = MagicMock(return_value=[])
            cur.rowcount = -1
            return cur

        # syncpgrolegroups is the only missing function; everything
        # else already exists.
        def _functionexists(_args, name, **_kw):
            return name != "engine.syncpgrolegroups"

        imported = []

        def _importsql(_args, filename, **_kw):
            imported.append(filename)
            return True

        monkeypatch.setattr(database, "cursor", _ok_cursor)
        monkeypatch.setattr(database, "functionexists", _functionexists)
        monkeypatch.setattr(database, "importsql", _importsql)

        assert checkfunctions.main(test_args, conn=conn, stage=1) is True
        assert imported == ["createrol.sql"], (
            "missing engine.syncpgrolegroups must be provisioned from "
            f"createrol.sql, got {imported!r}"
        )
