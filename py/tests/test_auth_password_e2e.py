"""
End-to-end test for the auth -> checkpassword hot path.

Exercises the *real* code (no mocks) against the live zoid6 database:

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

import pytest

from bbsengine6 import member as libmember
from bbsengine6.auth import access as auth_access


pytestmark = pytest.mark.requires_db


def _make_args(databasename: str = "zoid6") -> "argparse.Namespace":
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


def test_checkpassword_verifies_actual_setpassword_result(args, pool):
    """The full hot path:

    1. ``auth.access(op="login")`` — gate returns True.
    2. ``setpassword`` writes the password as a bcrypt hash.
    3. ``checkpassword`` verifies the plaintext against that hash.

    Uses the *real* production functions, not mocks.
    """
    plaintext = "12345"
    moniker = "jam"

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
    with psycopg.connect("dbname=zoid6") as verify_conn:
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


def test_checkpassword_rejects_legacy_md5_hash(args, pool):
    """Existing rows in the live DB use a mix of hash algorithms:

      * ``jam``           — ``$2$`` (bcrypt, written by the current
                              ``setpassword`` path).
      * ``__dealer__``    — ``$1$`` (legacy MD5, left over from older
                              hashing code).

    ``checkpassword`` must reject a plaintext that does not match the
    stored hash regardless of which algorithm produced it. This is a
    regression pin against any future change that would make
    ``checkpassword`` too permissive (e.g. a substring match, a
    ``LIKE '%plaintext%'`` leak, or a fallback that treats any
    non-empty stored value as accepted).
    """
    import psycopg
    with psycopg.connect("dbname=zoid6") as verify_conn:
        with verify_conn.cursor() as cur:
            cur.execute(
                "select moniker, password from engine.__member "
                "where moniker in ('jam', '__dealer__')"
            )
            rows = dict(cur.fetchall())

    jam_hash = rows["jam"]
    dealer_hash = rows["__dealer__"]

    assert jam_hash.startswith(("$2a$", "$2b$", "$2y$")), (
        f"jam must hold a bcrypt hash (the current setpassword output); "
        f"got prefix: {jam_hash[:3]!r}"
    )
    assert dealer_hash.startswith("$1$"), (
        f"__dealer__ must hold a legacy MD5 hash; got prefix: "
        f"{dealer_hash[:3]!r}"
    )

    assert (
        libmember.checkpassword(args, "anything", "jam", pool=pool) is False
    ), "no plaintext should match jam's bcrypt hash"
    assert (
        libmember.checkpassword(args, "anything", "__dealer__", pool=pool)
        is False
    ), "no plaintext should match __dealer__'s legacy MD5 hash"
    assert (
        libmember.checkpassword(args, "", "jam", pool=pool) is False
    ), "empty plaintext must never match a real hash"
    assert (
        libmember.checkpassword(args, "", "__dealer__", pool=pool) is False
    ), "empty plaintext must never match a real MD5 hash"
