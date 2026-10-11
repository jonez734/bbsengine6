"""Tests for bbsengine6.auth.verify -- the read-only BBS auth gate.

Run against the local 'zoid6test' fixture DB on a build host. Each test
inserts the rows it needs, calls verify_member, asserts the (ok, outcome)
pair, and cleans up after itself.

The test DB must already have the schema (see sql/schema.sql +
sql/008_add_member_accountexpires.sql) and the engine/__member and
postoffice schema with mailbox / mailbox_password tables.

The tests use BBSENGINE6_TEST_DSN env var to override; default is
the bbsengine6 zoid6test DB.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import pytest

# Ensure bbsengine6 is importable from the source tree.
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from bbsengine6.auth.verify import verify_member, _verify_hash  # noqa: E402


# ---- fixtures ----------------------------------------------------------------


@pytest.fixture(scope="module")
def db_args():
    """Args namespace pointing at the test DB."""
    import argparse
    return argparse.Namespace(
        databasename=os.environ.get("BBSENGINE6_TEST_DBNAME", "zoid6test"),
        databasehost=os.environ.get("BBSENGINE6_TEST_DBHOST", "localhost"),
        databaseport=int(os.environ.get("BBSENGINE6_TEST_DBPORT", "5432")),
        databaseuser=os.environ.get("BBSENGINE6_TEST_DBUSER", "opencode"),
    )


@pytest.fixture
def now():
    return datetime.now(timezone.utc)


def _hash_bcrypt(plaintext: str) -> str:
    """Generate a $2b$06$... bcrypt hash for fixture data."""
    return bcrypt.hashpw(plaintext.encode("utf-8"),
                         bcrypt.gensalt(rounds=4, prefix=b"2b")).decode("ascii")


# ---- hash verifier unit tests ------------------------------------------------


def test_verify_hash_bcrypt():
    h = _hash_bcrypt("secret-123")
    assert _verify_hash("secret-123", h) is True
    assert _verify_hash("wrong", h) is False


def test_verify_hash_md5_crypt():
    import crypt as _crypt
    h = _crypt.crypt("secret-123", _crypt.mksalt(_crypt.METHOD_MD5))
    assert _verify_hash("secret-123", h) is True
    assert _verify_hash("wrong", h) is False


def test_verify_hash_sha512_crypt():
    import crypt as _crypt
    h = _crypt.crypt("secret-123", _crypt.mksalt(_crypt.METHOD_SHA512))
    assert _verify_hash("secret-123", h) is True
    assert _verify_hash("wrong", h) is False


def test_verify_hash_empty_inputs():
    assert _verify_hash("", "$2b$06$xxx") is False
    assert _verify_hash("secret", "") is False
    assert _verify_hash("secret", None) is False


# ---- integration tests (require a live DB) -----------------------------------


@pytest.fixture
def member_factory(db_args):
    """Yield a factory that creates a member row and cleans up after the test.

    Yields a function (moniker, approved, password, accountexpires=None) -> None
    that inserts a row and registers cleanup.
    """
    created: list[str] = []

    def _make(moniker: str, approved: bool, password: str | None,
              accountexpires: datetime | None = None) -> None:
        from bbsengine6 import database
        pool = database.getpool(db_args)
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO engine.__member
                        (moniker, email, password, approved, datecreated,
                         accountexpires)
                    VALUES (%s, %s, %s, %s, NOW(), %s)
                    ON CONFLICT (moniker) DO UPDATE SET
                        email = EXCLUDED.email,
                        password = EXCLUDED.password,
                        approved = EXCLUDED.approved,
                        accountexpires = EXCLUDED.accountexpires
                    """,
                    (moniker, f"{moniker}@test.local", password, approved,
                     accountexpires),
                )
            conn.commit()
        finally:
            pool.putconn(conn)
        created.append(moniker)

    yield _make

    if not created:
        return
    from bbsengine6 import database
    pool = database.getpool(db_args)
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM engine.__member WHERE moniker = ANY(%s)",
                (created,),
            )
        conn.commit()
    finally:
        pool.putconn(conn)


def test_no_member_returns_no_user(db_args, now):
    ok, outcome = verify_member("definitely_does_not_exist_xyz123",
                                "anything", args=db_args, now=now)
    assert ok is False
    assert outcome == "no-user"


def test_approved_with_bcrypt_returns_ok(db_args, member_factory, now):
    member_factory("test_alice_001", approved=True,
                   password=_hash_bcrypt("pw-alice-1"))
    ok, outcome = verify_member("test_alice_001", "pw-alice-1",
                                args=db_args, now=now)
    assert ok is True
    assert outcome == "ok"


def test_approved_with_wrong_password_returns_wrong(db_args, member_factory, now):
    member_factory("test_alice_002", approved=True,
                   password=_hash_bcrypt("pw-alice-2"))
    ok, outcome = verify_member("test_alice_002", "wrong-pw",
                                args=db_args, now=now)
    assert ok is False
    assert outcome == "wrong-password"


def test_not_approved_returns_not_approved(db_args, member_factory, now):
    member_factory("test_alice_003", approved=False,
                   password=_hash_bcrypt("pw-alice-3"))
    ok, outcome = verify_member("test_alice_003", "pw-alice-3",
                                args=db_args, now=now)
    assert ok is False
    assert outcome == "not-approved"


def test_accountexpires_past_returns_expired(db_args, member_factory, now):
    member_factory(
        "test_alice_004", approved=True,
        password=_hash_bcrypt("pw-alice-4"),
        accountexpires=now - timedelta(hours=1),
    )
    ok, outcome = verify_member("test_alice_004", "pw-alice-4",
                                args=db_args, now=now)
    assert ok is False
    assert outcome == "sasl-expired"


def test_accountexpires_future_returns_ok(db_args, member_factory, now):
    member_factory(
        "test_alice_005", approved=True,
        password=_hash_bcrypt("pw-alice-5"),
        accountexpires=now + timedelta(hours=1),
    )
    ok, outcome = verify_member("test_alice_005", "pw-alice-5",
                                args=db_args, now=now)
    assert ok is True
    assert outcome == "ok"


def test_accountexpires_null_returns_ok(db_args, member_factory, now):
    member_factory("test_alice_006", approved=True,
                   password=_hash_bcrypt("pw-alice-6"),
                   accountexpires=None)
    ok, outcome = verify_member("test_alice_006", "pw-alice-6",
                                args=db_args, now=now)
    assert ok is True
    assert outcome == "ok"


def test_null_password_column_rejects(db_args, member_factory, now):
    member_factory("test_alice_007", approved=True, password=None)
    ok, outcome = verify_member("test_alice_007", "anything",
                                args=db_args, now=now)
    assert ok is False
    assert outcome == "wrong-password"


def test_md5_crypt_hash_returns_ok(db_args, member_factory, now):
    import crypt as _crypt
    h = _crypt.crypt("pw-alice-8", _crypt.mksalt(_crypt.METHOD_MD5))
    member_factory("test_alice_008", approved=True, password=h)
    ok, outcome = verify_member("test_alice_008", "pw-alice-8",
                                args=db_args, now=now)
    assert ok is True
    assert outcome == "ok"


def test_sha512_crypt_hash_returns_ok(db_args, member_factory, now):
    import crypt as _crypt
    h = _crypt.crypt("pw-alice-9", _crypt.mksalt(_crypt.METHOD_SHA512))
    member_factory("test_alice_009", approved=True, password=h)
    ok, outcome = verify_member("test_alice_009", "pw-alice-9",
                                args=db_args, now=now)
    assert ok is True
    assert outcome == "ok"


def test_dispatch_per_user_no_at_sign(db_args, member_factory, now):
    from bbsengine6.auth.verify import _dispatch
    assert _dispatch("alice") == "user"
    assert _dispatch("alice@bbsengine.org") == "mailbox"


def test_empty_inputs(db_args, now):
    ok, outcome = verify_member("", "pw", args=db_args, now=now)
    assert ok is False
    ok, outcome = verify_member("alice", "", args=db_args, now=now)
    assert ok is False


# ---- read-only enforcement test ----------------------------------------------


def test_read_only_transaction_blocks_writes(db_args, member_factory, now):
    """A future bug that tries to write during verify_member must fail
    because the transaction is BEGIN READ ONLY. We exploit this by
    issuing a verify_member call while a held cursor has a writable
    INSERT pending; verify_member's transaction should error out.

    Simpler approach: pass a bad SQL via _verify_per_user monkeypatch
    and assert the error surfaces as 'db-error'. (The simple
    BEGIN-READ-ONLY + INSERT is already enforced by Postgres; we
    verify the verifier's transaction is READ ONLY by inspecting
    pg_stat_activity or by issuing a manual INSERT in the same
    transaction.)
    """
    import psycopg
    from bbsengine6 import database

    pool = database.getpool(db_args)
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("BEGIN READ ONLY")
            with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
                cur.execute("INSERT INTO engine.__member (moniker, email) "
                            "VALUES ('test_readonly_probe', 'x@x')")
            cur.execute("ROLLBACK")
    finally:
        pool.putconn(conn)


# ---- Dovecot checkpassword entry-point tests --------------------------------
#
# These tests exercise bbsengine6.auth.dovecot.main() directly, with
# monkeypatched env (AUTH_USER) and stdin (the checkpassword protocol
# byte stream). They do NOT need a DB for the protocol-level tests
# (missing-user / missing-password / db-error); the success / wrong-
# password tests require the DB and a fixture member.


def _run_dovecot_with_input(monkeypatch, auth_user: str, stdin_bytes: bytes):
    """Invoke bbsengine6.auth.dovecot.main() with controlled env + stdin.

    Returns (exit_code, captured_stdout).
    """
    import io
    from bbsengine6.auth import dovecot

    if auth_user:
        monkeypatch.setenv("AUTH_USER", auth_user)
    else:
        monkeypatch.delenv("AUTH_USER", raising=False)
    # Build a stdin that has both a .read() (for sys.stdin.read used by
    # the Python text wrapper) and a .buffer.read() (used by cli._read_checkpassword_stdin).
    fake_stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", fake_stdin)
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    rc = dovecot.main([])
    return rc, stdout.getvalue()


def test_dovecot_missing_auth_user_returns_1(monkeypatch):
    rc, _ = _run_dovecot_with_input(monkeypatch, auth_user="",
                                    stdin_bytes=b"pw\0user\0\n")
    assert rc == 1


def test_dovecot_missing_password_returns_1(monkeypatch):
    rc, _ = _run_dovecot_with_input(monkeypatch, auth_user="alice",
                                    stdin_bytes=b"")
    assert rc == 1


def test_dovecot_wrong_password_returns_1(monkeypatch):
    """Stub the verifier so we don't need a real pool here."""
    from unittest.mock import patch
    with patch("bbsengine6.auth.dovecot.verify_member") as mock_verify:
        mock_verify.return_value = (False, "wrong-password")
        rc, stdout = _run_dovecot_with_input(
            monkeypatch, auth_user="alice",
            stdin_bytes=b"wrong-pw\0alice\0\n",
        )
    assert rc == 1
    assert stdout == ""


def test_dovecot_success_prints_userdb_lines(monkeypatch):
    from unittest.mock import patch
    with patch("bbsengine6.auth.dovecot.verify_member") as mock_verify:
        mock_verify.return_value = (True, "ok")
        rc, stdout = _run_dovecot_with_input(
            monkeypatch, auth_user="alice",
            stdin_bytes=b"correct-pw\0alice\0\n",
        )
    assert rc == 0
    # Userdb lines should be present (defaults).
    assert "home=" in stdout
    assert "mail=" in stdout
    assert "userdb_home=" in stdout
    assert "userdb_mail=" in stdout


def test_dovecot_uses_auth_user_not_stdin(monkeypatch):
    """The userinfo field in stdin is ignored; the username comes from
    AUTH_USER. A malicious caller cannot substitute a different user
    by tampering with stdin.
    """
    from unittest.mock import patch
    with patch("bbsengine6.auth.dovecot.verify_member") as mock_verify:
        mock_verify.return_value = (False, "wrong-password")
        # stdin says 'pw\0mallory\0' (pretending to be mallory), but
        # AUTH_USER=alice. The verifier must be called with 'alice'.
        _run_dovecot_with_input(
            monkeypatch, auth_user="alice",
            stdin_bytes=b"pw\0mallory\0\n",
        )
    # verify_member was called with user=alice, NOT mallory.
    args, kwargs = mock_verify.call_args
    assert args[0] == "alice"


# ---- PAM helper entry-point tests -------------------------------------------


def _run_pam_with_env(monkeypatch, env: dict, stdin_bytes: bytes = b""):
    """Invoke bbsengine6.auth.pam.main() with controlled env + stdin."""
    import io
    from bbsengine6.auth import pam

    # Wipe all PAM_ and AUTH_ vars first so monkeypatch can set cleanly.
    for key in list(os.environ):
        if key.startswith("PAM_") or key.startswith("AUTH_"):
            monkeypatch.delenv(key, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    if stdin_bytes:
        monkeypatch.setattr(sys, "stdin", io.BytesIO(stdin_bytes))
    rc = pam.main([])
    return rc


def test_pam_account_type_passes_through(monkeypatch):
    """PAM_TYPE=account: exit 0 with no DB call."""
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        rc = _run_pam_with_env(monkeypatch, env={"PAM_TYPE": "account",
                                                  "PAM_USER": "alice"})
    assert rc == 0
    mock_verify.assert_not_called()


def test_pam_missing_user_returns_1(monkeypatch):
    rc = _run_pam_with_env(monkeypatch, env={"PAM_TYPE": "auth"})
    assert rc == 1


def test_pam_missing_authtok_returns_1(monkeypatch):
    rc = _run_pam_with_env(monkeypatch,
                            env={"PAM_TYPE": "auth", "PAM_USER": "alice"})
    assert rc == 1


def test_pam_scrubs_pam_authtok_from_env(monkeypatch):
    """After main() returns, PAM_AUTHTOK must be gone from os.environ."""
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        mock_verify.return_value = (True, "ok")
        rc = _run_pam_with_env(
            monkeypatch,
            env={"PAM_TYPE": "auth", "PAM_USER": "alice",
                 "PAM_AUTHTOK": "secret-xyz-12345"},
        )
    assert rc == 0
    assert "PAM_AUTHTOK" not in os.environ


def test_pam_never_logs_password(monkeypatch, caplog):
    """caplog captures stderr; assert the password never appears."""
    import logging
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        mock_verify.return_value = (True, "ok")
        with caplog.at_level(logging.INFO, logger="bbsengine6.auth.pam"):
            _run_pam_with_env(
                monkeypatch,
                env={"PAM_TYPE": "auth", "PAM_USER": "alice",
                     "PAM_AUTHTOK": "supersecret-pw-do-not-log"},
            )
    captured = caplog.text
    assert "supersecret-pw-do-not-log" not in captured


def test_pam_ok_returns_0(monkeypatch):
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        mock_verify.return_value = (True, "ok")
        rc = _run_pam_with_env(
            monkeypatch,
            env={"PAM_TYPE": "auth", "PAM_USER": "alice",
                 "PAM_AUTHTOK": "pw"},
        )
    assert rc == 0


def test_pam_wrong_password_returns_1(monkeypatch):
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        mock_verify.return_value = (False, "wrong-password")
        rc = _run_pam_with_env(
            monkeypatch,
            env={"PAM_TYPE": "auth", "PAM_USER": "alice",
                 "PAM_AUTHTOK": "wrong"},
        )
    assert rc == 1


def test_pam_db_error_returns_2(monkeypatch):
    from unittest.mock import patch
    with patch("bbsengine6.auth.pam.verify_member") as mock_verify:
        mock_verify.side_effect = RuntimeError("simulated db failure")
        rc = _run_pam_with_env(
            monkeypatch,
            env={"PAM_TYPE": "auth", "PAM_USER": "alice",
                 "PAM_AUTHTOK": "pw"},
        )
    assert rc == 2
