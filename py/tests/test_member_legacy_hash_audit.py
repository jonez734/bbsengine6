"""
Regression test for ``bbsengine6.member.audit_password_column``.

The 2026-08-22 ``bed auth login`` incident diagnosed a 34-char ``$1$``
MD5-crypt hash in ``engine.__member.password`` that defeated the bcrypt
round-trip in ``member.checkpassword``. The remediation requires:

  1. Migrate any other legacy ``$1$`` rows to bcrypt (one-shot scan).
  2. Run this audit query against the live DB; the result must be empty.

This test pins both the SQL pattern and the empty-result invariant. If
a future code path reintroduces a legacy MD5-crypt hash, the live-DB
assertion in this file fails and the operator is alerted.

Unit tests verify the SQL pattern matches the discovery query documented
in ``zoid6/TODO.md`` "Password column hardening":

    SELECT moniker
      FROM engine.__member
     WHERE password IS NOT NULL
       AND password ~ '^\\$1\\$';

Live-DB test (gated by ``@pytest.mark.requires_db``) runs the real
``audit_password_column`` against the live ``zoid6`` database and asserts
the result is empty. The conftest's per-test ``db_connection.rollback()``
keeps any changes from persisting.
"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bbsengine6 import member as libmember


# Note: NO module-level pytest.mark.unit — the live-DB regression pin at
# the bottom of this file is requires_db-marked and must run when a live
# DB is available. The unit cases below are individually marked.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_args(**overrides):
    defaults = dict(
        debug=False,
        databasename="zoid6test",
        databasehost="localhost",
        databaseport=5432,
        databaseschema="engine",
    )
    defaults.update(overrides)
    return Mock(**defaults)


class _SpyCursor:
    """Cursor stand-in that returns preset rows and records execute() calls.

    Used to verify the audit SQL pattern (regex match, NULL exclusion,
    engine.member schema) without touching a real database.
    """

    def __init__(self, rows):
        self._rows = list(rows)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchall(self):
        return list(self._rows)


class _SpyConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, **kw):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    @property
    def autocommit(self):
        return False

    @autocommit.setter
    def autocommit(self, value):
        pass

    @property
    def pgconn(self):
        m = Mock()
        m.transaction_status = 0
        return m


# ---------------------------------------------------------------------------
# Unit tests (no DB)
# ---------------------------------------------------------------------------


@pytest.fixture
def args():
    return _make_args()


@pytest.mark.unit
def test_audit_password_column_returns_empty_when_no_legacy_rows(args):
    """Healthy DB (zero legacy MD5-crypt rows) returns an empty list."""
    cursor = _SpyCursor(rows=[])
    rows = libmember.audit_password_column(args, cur=cursor)

    assert rows == [], (
        "audit_password_column must return [] when no rows match the regex"
    )
    assert len(cursor.calls) == 1, (
        "audit must issue exactly one SELECT; got "
        f"{len(cursor.calls)} calls"
    )


@pytest.mark.unit
def test_audit_password_column_returns_matching_monikers(args):
    """A DB with legacy MD5-crypt rows returns the matching monikers."""
    cursor = _SpyCursor(rows=[{"moniker": "alice"}, {"moniker": "__dealer__"}])
    rows = libmember.audit_password_column(args, cur=cursor)

    assert rows == ["alice", "__dealer__"], (
        f"audit must return every matching moniker; got {rows!r}"
    )


@pytest.mark.unit
def test_audit_password_column_uses_engine_member_schema(args):
    """The SQL must target engine.member (the view over __member) and use
    the configured schema via _qualified()."""
    cursor = _SpyCursor(rows=[])
    libmember.audit_password_column(args, cur=cursor)

    rendered = cursor.calls[0][0]
    sql_text = (
        rendered.as_string(None)
        if hasattr(rendered, "as_string")
        else str(rendered)
    )
    sql_lower = sql_text.lower()

    assert "from" in sql_lower, f"audit must be a SELECT; got: {sql_text!r}"
    assert "engine" in sql_lower and "member" in sql_lower, (
        f"audit must target engine.member; got: {sql_text!r}"
    )
    assert "where" in sql_lower, f"audit must filter; got: {sql_text!r}"


@pytest.mark.unit
def test_audit_password_column_excludes_null_passwords(args):
    """The SQL must exclude NULL password rows so unset-password members
    don't pollute the audit result."""
    cursor = _SpyCursor(rows=[])
    libmember.audit_password_column(args, cur=cursor)

    rendered = cursor.calls[0][0]
    sql_text = (
        rendered.as_string(None)
        if hasattr(rendered, "as_string")
        else str(rendered)
    )
    sql_lower = sql_text.lower()

    assert "password is not null" in sql_lower or "password is not null" in sql_text.lower(), (
        f"audit must exclude NULL passwords; got: {sql_text!r}"
    )


@pytest.mark.unit
def test_audit_password_column_filters_on_dollar_one_prefix(args):
    """The regex filter must match exactly ``$1$`` (legacy MD5-crypt), not
    a broader pattern that would catch bcrypt ($2a$, $2b$, $2y$)."""
    cursor = _SpyCursor(rows=[])
    libmember.audit_password_column(args, cur=cursor)

    rendered = cursor.calls[0][0]
    sql_text = (
        rendered.as_string(None)
        if hasattr(rendered, "as_string")
        else str(rendered)
    )

    assert "\\$1" in sql_text or "1\\$" in sql_text, (
        f"audit regex must include the $1$ MD5-crypt prefix; got: {sql_text!r}"
    )
    assert "$2a$" not in sql_text and "$2b$" not in sql_text, (
        f"audit regex must NOT include bcrypt prefixes; got: {sql_text!r}"
    )


@pytest.mark.unit
def test_audit_password_column_uses_existing_cursor_no_new_connection(
    args, monkeypatch
):
    """audit_password_column must use the cursor passed via cur= kwarg;
    never open a new connection. Mirrors the CONN_POOL_PATTERN contract."""
    cursor = _SpyCursor(rows=[])
    rows = libmember.audit_password_column(args, cur=cursor)

    assert rows == []
    assert len(cursor.calls) == 1, (
        f"audit must issue exactly one SELECT; got {len(cursor.calls)} calls"
    )


# ---------------------------------------------------------------------------
# Live-DB test (gated)
# ---------------------------------------------------------------------------


@pytest.mark.requires_db
def test_audit_password_column_returns_no_legacy_md5_in_live_db(pool):
    """Live ``zoid6`` database must hold zero legacy ``$1$`` MD5-crypt hashes.

    If this fails, the operator should:

      1. Note the listed monikers from ``audit_password_column(args, pool=pool)``.
      2. Run ``bbsengine6/scripts/setpassword.py <moniker> <newpassword>``
         for each, OR contact the member to self-rotate via the standard
         password-change flow.

    Until then, ``checkpassword`` for those monikers will silently fail
    (crypt with $1$ prefix selects MD5-crypt, not bcrypt), exactly the
    2026-08-22 incident symptom.

    The conftest's ``test_transaction`` autouse fixture rolls back at
    the end of the test, so even if the query itself somehow modifies
    state the live DB is untouched.
    """
    import argparse
    import getpass

    parser = argparse.ArgumentParser()
    defaults = {
        "databasename": "zoid6",
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
        "databaseschema": "engine",
    }
    from bbsengine6 import database as db_mod

    db_mod.buildargdatabasegroup(parser, defaults)
    args = parser.parse_args([])

    rows = libmember.audit_password_column(args, pool=pool)

    assert rows == [], (
        f"engine.__member holds {len(rows)} legacy $1$ MD5-crypt hash(es): "
        f"{rows!r}. Migrate each via "
        f"bbsengine6/scripts/setpassword.py before this assertion can pass. "
        f"See zoid6/TODO.md 'Password column hardening — legacy MD5-crypt "
        f"migration' item 1."
    )
