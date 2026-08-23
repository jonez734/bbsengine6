"""Tests for ``bbsengine6.database.constraintexists``.

The helper is a schema-filtered lookup against
``pg_constraint`` joined to ``pg_namespace`` so two schemas with the
same constraint name do not collide. Mirrors the shape of the
sibling helpers (``classexists``, ``functionexists``, ``typeexists``,
``schemaexists``) so it follows the same CONN_POOL_PATTERN: resolves
a cursor from kwargs in priority order ``conn`` -> ``pool`` ->
``args``.

Coverage:

  * True when the named constraint exists in the requested schema.
  * False when the constraint is absent from the schema.
  * False when the same-named constraint lives in a different
    schema (proves the pg_namespace join is actually filtering).
  * No-conn / no-pool error path returns False (defensive default
    used by checkpasswordformat when the stage_one conn is None).
  * Exception path returns False (mirrors the try/except in
    ``functionexists`` so a broken DB doesn't crash startup).
"""

from __future__ import annotations

import argparse
import getpass
import os
from unittest.mock import MagicMock

import pytest

from bbsengine6 import database


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_args():
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


def _configured_cursor(rowcount: int, row=None):
    """Build a cursor whose ``rowcount`` and ``fetchone`` are pre-set.

    Used to simulate the various outcomes of
    ``constraintexists``'s SELECT without spinning up a real DB.
    """
    state = {"rowcount": rowcount, "row": row}

    class _Cur:
        def __init__(self):
            self.execute = MagicMock()
            self._state = state

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        @property
        def rowcount(self):
            return self._state["rowcount"]

        def fetchone(self):
            return self._state["row"]

    return _Cur()


# ---------------------------------------------------------------------------
# Positive / negative path
# ---------------------------------------------------------------------------


class TestConstraintexists:
    """Direct coverage for the helper."""

    def test_returns_true_when_constraint_present(
        self, test_args, monkeypatch
    ):
        cur = _configured_cursor(rowcount=1, row={"x": 1})
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.constraintexists(
            test_args,
            "engine",
            "chk_member_password_bcrypt",
            conn=conn,
        )
        assert result is True

    def test_returns_false_when_constraint_absent(
        self, test_args, monkeypatch
    ):
        cur = _configured_cursor(rowcount=0)
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        result = database.constraintexists(
            test_args,
            "engine",
            "chk_member_password_bcrypt",
            conn=conn,
        )
        assert result is False

    def test_returns_false_when_constraint_in_other_schema(
        self, test_args, monkeypatch
    ):
        """Pin the pg_namespace join: the SQL must filter by
        ``n.nspname = %s`` so a constraint named the same in another
        schema does not give a false positive.

        We exercise this by asserting the SQL contains the namespace
        join clause and that the second bind parameter (the schema
        name) is passed through verbatim.
        """
        cur = _configured_cursor(rowcount=0)
        monkeypatch.setattr(database, "cursor", lambda *a, **kw: cur)

        conn = MagicMock(name="conn")
        database.constraintexists(
            test_args,
            "public",
            "chk_member_password_bcrypt",
            conn=conn,
        )

        sql_arg = cur.execute.call_args[0][0]
        params = cur.execute.call_args[0][1]
        assert "pg_constraint" in sql_arg
        assert "pg_namespace" in sql_arg
        assert "n.nspname" in sql_arg
        assert "c.conname" in sql_arg
        assert params == ("chk_member_password_bcrypt", "public")

    def test_returns_false_when_no_conn_no_pool(
        self, test_args
    ):
        """Defensive default: if neither conn nor pool is supplied,
        the helper must return False rather than raise. checkpasswordformat
        relies on this when the stage_one conn is None at module-init
        time."""
        result = database.constraintexists(
            test_args,
            "engine",
            "chk_member_password_bcrypt",
        )
        assert result is False

    def test_returns_false_on_exception(
        self, test_args, monkeypatch
    ):
        """A broken DB must not crash startup; the helper mirrors
        functionexists' try/except and returns False on any error."""

        def _boom_cursor(*_a, **_kw):
            raise RuntimeError("simulated DB unavailable")

        monkeypatch.setattr(database, "cursor", _boom_cursor)

        conn = MagicMock(name="conn")
        result = database.constraintexists(
            test_args,
            "engine",
            "chk_member_password_bcrypt",
            conn=conn,
        )
        assert result is False
