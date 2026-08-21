"""
Tests for bbsengine6.member.verifyMemberFound and verifyMemberNotFound.

Both functions require a ``pool=`` keyword argument. The caller owns
the pool. If ``pool=`` is omitted, the function logs an error and
returns ``None``.

The functions are read-only checks against ``engine.member`` and do not
wrap the read in a transaction.

Test tiers
----------

``@pytest.mark.unit`` tests
    In-memory only. Use a fake pool to verify the SQL string the
    read sends to the cursor, and the error paths.

Integration tests (no marker)
    Use the ``zoid6test`` database to verify that the read returns
    the correct True/False for existing and non-existing members.
    The conftest's per-test transaction rollback keeps the
    engine.__member table clean.
"""

from __future__ import annotations

import argparse
import getpass
from contextlib import contextmanager

import pytest

from bbsengine6 import database, member as member_module


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def make_test_args(databasename: str = "zoid6test") -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", default=False)
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture(scope="function")
def test_args() -> argparse.Namespace:
    return make_test_args()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def _fake_conn_with_cursor(captured: dict, rowcount: int):
    """Build a stub conn whose .transaction() is a no-op context manager
    and whose cursor factory returns a FakeCursor that records the
    executed query and reports the given rowcount."""

    @contextmanager
    def fake_transaction(**kwargs):
        yield

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, q, params=None):
            captured["query"] = q
            captured["params"] = params
            self.rowcount = rowcount

    class FakeConn:
        def transaction(self, **kwargs):
            return fake_transaction()

    return FakeConn(), lambda conn: FakeCursor()


@pytest.mark.unit
def test_emits_select_against_schema_member_keyed_on_loginid() -> None:
    """The read must issue a SELECT 1 against <schema>.member keyed on loginid,
    with the value bound as a psycopg3 %s parameter (not inlined as a literal).

    Regression pin for the password-path hardening: the auth hot path now
    uses cur.execute(sql, params) so the value never flows through the
    database.query() regex-replacement layer.
    """
    test_args = make_test_args()
    captured = {}
    fake_conn, fake_cursor = _fake_conn_with_cursor(captured, rowcount=1)

    @contextmanager
    def fake_connect(args, pool, **kwargs):
        yield fake_conn

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(database, "connect", fake_connect)
        mp.setattr(database, "cursor", fake_cursor)
        result = member_module.verifyMemberFound(test_args, "alice", pool=object())

    assert result is True, "Existing member should return True"
    rendered = captured["query"].as_string(None)
    assert rendered == (
        f'select 1 from "{test_args.databaseschema}"."member" '
        "where loginid = %s"
    )
    assert captured["params"] == ("alice",), (
        "value must be bound as a separate parameter tuple, not inlined "
        "into the SQL string"
    )


@pytest.mark.unit
def test_accepts_column_kwarg_for_moniker() -> None:
    """column='moniker' must flow into the WHERE clause."""
    test_args = make_test_args()
    captured = {}
    fake_conn, fake_cursor = _fake_conn_with_cursor(captured, rowcount=0)

    @contextmanager
    def fake_connect(args, pool, **kwargs):
        yield fake_conn

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(database, "connect", fake_connect)
        mp.setattr(database, "cursor", fake_cursor)
        result = member_module.verifyMemberFound(
            test_args, "ghost", column="moniker", pool=object()
        )

    assert result is False
    assert "where moniker" in captured["query"].as_string(None)


@pytest.mark.unit
def test_returns_none_on_unexpected_exception(test_args) -> None:
    """Any exception during the read logs a traceback and returns None."""
    @contextmanager
    def fake_transaction(**kwargs):
        yield

    class BrokenCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, q, params=None):
            raise RuntimeError("boom")

    class FakeConn:
        def transaction(self, **kwargs):
            return fake_transaction()

    @contextmanager
    def fake_connect(args, pool, **kwargs):
        yield FakeConn()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(database, "connect", fake_connect)
        mp.setattr(database, "cursor", lambda conn: BrokenCursor())
        result = member_module.verifyMemberFound(test_args, "alice", pool=object())

    assert result is None


@pytest.mark.unit
def test_returns_none_when_no_pool(test_args) -> None:
    """If pool= is not given, the function logs an error and returns None."""
    result = member_module.verifyMemberFound(test_args, "alice")
    assert result is None


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_finds_existing_member_by_moniker(test_args, pool) -> None:
    """Returns True for a member already present in engine.__member."""
    user = getpass.getuser()
    existing = f"test_{user}_1"

    assert (
        member_module.verifyMemberFound(
            test_args, existing, column="moniker", pool=pool
        )
        is True
    )


def test_finds_existing_member_by_email(test_args, pool) -> None:
    """Works for non-moniker columns too."""
    user = getpass.getuser()
    email = f"test_{user}_1@test.local"

    assert (
        member_module.verifyMemberFound(
            test_args, email, column="email", pool=pool
        )
        is True
    )


def test_returns_false_for_missing_member(test_args, pool) -> None:
    """Returns False for a moniker that was never inserted."""
    assert (
        member_module.verifyMemberFound(
            test_args,
            "no_such_member_xyzzy",
            column="moniker",
            pool=pool,
        )
        is False
    )


def test_notfound_is_inverse_of_found(test_args, pool) -> None:
    """verifyMemberNotFound and verifyMemberFound must return opposite
    results for the same input."""
    user = getpass.getuser()
    existing = f"test_{user}_1"
    missing = "no_such_member_xyzzy"

    found_present = member_module.verifyMemberFound(
        test_args, existing, column="moniker", pool=pool
    )
    notfound_present = member_module.verifyMemberNotFound(
        test_args, existing, column="moniker", pool=pool
    )
    found_missing = member_module.verifyMemberFound(
        test_args, missing, column="moniker", pool=pool
    )
    notfound_missing = member_module.verifyMemberNotFound(
        test_args, missing, column="moniker", pool=pool
    )

    assert found_present is True
    assert notfound_present is False
    assert found_missing is False
    assert notfound_missing is True
