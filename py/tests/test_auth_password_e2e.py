"""
End-to-end test for the auth -> checkpassword hot path.

Exercises the *real* code (no mocks) against the test database (BBSENGINE6_TEST_DB, default zoid6test):

  1. ``bbsengine6.auth.access(args, "login", session=..., message=...)``
     — the policy gate that the bed WS handler routes through before
     credential checking.

  2. ``bbsengine6.member.setpassword(args, plaintext, moniker, pool=pool)``
     — the production password-write path used by console.member.add/edit
     and engine/join.php. Issues
     ``UPDATE engine.__member SET password = crypt(?, gen_salt('bf'))``.

  3. ``bbsengine6.member.checkpassword(args, plaintext, moniker, pool=pool)``
     — the production password-read path. Issues
     ``SELECT 1 FROM engine.member WHERE password = crypt(?, password)``.

The conftest's per-test ``db_connection.rollback()`` keeps the live
``engine.__member`` row untouched after the test.

This test is the integration companion to the SQL-layer test in
``test_console_member_add_edit.py::TestConsoleMemberPasswordEncryption``:
that one inspects the rendered SQL for the encryption pattern; this one
exercises the same SQL against a real PostgreSQL+pgcrypto to prove the
hash is stored correctly and verifies on retrieval.
"""

from __future__ import annotations

import getpass
import os

import pytest

from bbsengine6 import member as libmember
from bbsengine6.auth import access as auth_access


pytestmark = pytest.mark.requires_db


TEST_DBNAME = os.environ.get("BBSENGINE6_TEST_DBNAME") or os.environ.get("BBSENGINE6_TEST_DB", "zoid6test")


def _make_args(databasename: str = TEST_DBNAME) -> "argparse.Namespace":
    """Build a minimal ``argparse.Namespace`` that matches the conftest pool."""
    import argparse
    from bbsengine6 import database

    parser = argparse.ArgumentParser()
    defaults = {
        "databasename": databasename,
        "databasehost": "/var/run/postgresql",
        "databaseport": 5432,
        "databaseuser": getpass.getuser(),
        "databasepassword": None,
        "databaseschema": "engine",
    }
    database.buildargdatabasegroup(parser, defaults)
    return parser.parse_args([])


@pytest.fixture
def args():
    return _make_args()


def test_auth_login_gate_allows_credential_attempt(args):
    """``auth.access(op="login")`` is a free pass — the credential provider
    (here, ``member.checkpassword``) decides. The auth gate must NOT
    block the attempt; it just routes it through."""
    # session=None: an unbound websocket trying to log in.
    msg = {"type": "auth", "moniker": "jam", "password": "12345"}
    assert auth_access(args, "login", session=None, message=msg) is True

    # session bound to a different moniker: still allowed (login is free).
    session = type("S", (), {"moniker": "alice", "is_sysop": False, "session_id": None})()
    assert auth_access(args, "login", session=session, message=msg) is True

    # sysop session: still allowed.
    sysop = type("S", (), {"moniker": "sysop", "is_sysop": True, "session_id": "sx"})()
    assert auth_access(args, "login", session=sysop, message=msg) is True


def test_checkpassword_verifies_actual_setpassword_result(args, pool, create_test_users, test_users):
    """The full hot path:

    1. ``auth.access(op="login")`` — gate returns True.
    2. ``setpassword`` writes the password as a bcrypt hash.
    3. ``checkpassword`` verifies the plaintext against that hash.

    Uses the *real* production functions, not mocks. Writes only to the
    ``test_{user}_1`` fixture member, never to a real account.
    """
    plaintext = "12345"
    moniker = test_users[0]

    # Gate passes.
    msg = {"type": "auth", "moniker": moniker, "password": plaintext}
    assert auth_access(args, "login", session=None, message=msg) is True

    # Write the password through the production path. setpassword runs
    # ``UPDATE engine.__member SET password = crypt(?, gen_salt('bf'))
    # WHERE moniker = ?`` against the live DB.
    assert libmember.setpassword(args, plaintext, moniker, pool=pool) is True

    # Verify the row was actually written as a bcrypt hash (not
    # plaintext) by reading it back via a fresh cursor.
    import psycopg
    with psycopg.connect(f"dbname={TEST_DBNAME}") as verify_conn:
        with verify_conn.cursor() as cur:
            cur.execute(
                "select password from engine.__member where moniker = %s",
                (moniker,),
            )
            row = cur.fetchone()
    assert row is not None, "setpassword should have written the row"
    stored = row[0]
    assert stored is not None and stored != plaintext, (
        "stored value must NOT be plaintext; the production setpassword "
        "must encrypt via crypt(?, gen_salt('bf'))"
    )
    assert stored.startswith(("$2a$", "$2b$", "$2y$")), (
        f"stored value must be a bcrypt hash; got: {stored!r}"
    )

    # The actual credential check via the production code path.
    assert (
        libmember.checkpassword(args, plaintext, moniker, pool=pool) is True
    ), "checkpassword must accept the plaintext we just set"

    # Wrong password is rejected by the same code path.
    assert (
        libmember.checkpassword(args, "wrong", moniker, pool=pool) is False
    ), "checkpassword must reject any other plaintext"

    # Empty plaintext is rejected (no false positives on a real hash).
    assert (
        libmember.checkpassword(args, "", moniker, pool=pool) is False
    )


def test_checkpassword_rejects_wrong_and_empty_plaintext(args, pool, create_test_users, test_users):
    """``checkpassword`` must reject a plaintext that does not match the stored hash.

    The schema now allows only bcrypt hashes (``chk_member_password_bcrypt``, from
    manage_password_format.sql), so a legacy ``$1$`` row cannot be stored. This test
    pins the bcrypt rejection path and the schema rule. It writes only to a fixture
    member and restores that member's password afterward.
    """
    import psycopg

    from bbsengine6 import util

    moniker = test_users[1]
    bcrypt_hash = util.encryptpassword("12345")
    assert bcrypt_hash.startswith(("$2a$", "$2b$", "$2y$"))

    sql = "update engine.__member set password=%s where moniker=%s"
    with psycopg.connect(f"dbname={TEST_DBNAME}") as conn:
        with conn.cursor() as cur:
            cur.execute("select password from engine.__member where moniker = %s", (moniker,))
            before = cur.fetchone()[0]
            cur.execute(sql, (bcrypt_hash, moniker))
        conn.commit()

    try:
        assert libmember.checkpassword(args, "wrong", moniker, pool=pool) is False
        assert libmember.checkpassword(args, "", moniker, pool=pool) is False
    finally:
        with psycopg.connect(f"dbname={TEST_DBNAME}") as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (before, moniker))
            conn.commit()
