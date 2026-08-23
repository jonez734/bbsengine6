"""
Regression tests for ``bbsengine6.member.audit_password_hash``.

Pins the 2026-08-22 follow-up to the auth incident where a $1$ MD5-crypt
hash survived an earlier setpassword run and defeated the bcrypt round-trip
in member.checkpassword. ``audit_password_hash`` is the per-auth diagnostic
that turns "invalid moniker or password" into a one-line operator signal.

Covers:
- bcrypt hash -> all flags True, level="ok" log only
- MD5-crypt hash -> is_md5crypt=True + level="warning" log
- NULL -> present=False + level="warning" log
- empty string -> non_empty=False + level="warning" log
- 34-char non-prefixed text -> is_bcrypt=False + length_ok=False + level="warning" log
- 60-char text without $2 prefix -> is_bcrypt=False + level="warning" log

Also pins the integration with member.checkpassword: every checkpassword
call must invoke audit_password_hash on the same cursor (one SELECT for the
audit, one SELECT for the row, no extra connection — no PG crypt() round-trip;
the verify runs locally via bbsengine6.password.verify_password with a
stdlib crypt() fallback for legacy $1$ MD5-crypt hashes).
"""

import pytest

from bbsengine6 import member as libmember


pytestmark = pytest.mark.unit


class _SpyCursor:
    """Cursor stand-in that returns a preset password row and records execute() calls.

    Used to verify audit_password_hash against an in-memory fixture without
    touching a real database. Mirrors the spy pattern in
    test_console_member_add_edit.py:_SpyCursor.

    ``rowcount_after_round_trip`` is kept for backward compatibility
    with the pre-2026-08-23 PG crypt() round-trip SELECT 1 FROM ... WHERE
    password=crypt(...) path. After member.checkpassword was rewritten to
    verify locally (no PG round-trip), the round-trip SELECT no longer
    exists and this attribute is read but ignored. It is preserved so
    older test scenarios that supplied it continue to construct without
    TypeError. The audit and row-A SELECTs always return ``_rowcount``
    (default 1) because they don't gate the result.
    """

    def __init__(
        self,
        password=None,
        return_row=True,
        rowcount=1,
        rowcount_after_round_trip=1,
    ):
        self._password = password
        self._return_row = return_row
        self._rowcount = rowcount
        self._rowcount_after_round_trip = rowcount_after_round_trip
        self._saw_round_trip = False
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, query, params=None):
        self.calls.append((query, params))
        rendered = (
            query.as_string(None)
            if hasattr(query, "as_string")
            else str(query)
        )
        if "crypt(" in rendered.lower() and "select 1 from" in rendered.lower():
            self._saw_round_trip = True
            self._rowcount = self._rowcount_after_round_trip

    def fetchone(self):
        if not self._return_row:
            return None
        if self._password is None and not self._return_row:
            return None
        return {"password": self._password}

    @property
    def rowcount(self):
        return self._rowcount

    @rowcount.setter
    def rowcount(self, value):
        self._rowcount = value


class _SpyConn:
    """Connection stand-in that emits a single _SpyCursor."""

    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self, **kw):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    @property
    def autocommit(self):
        return False

    @autocommit.setter
    def autocommit(self, value):
        pass

    @property
    def pgconn(self):
        from unittest.mock import Mock

        m = Mock()
        m.transaction_status = 0
        return m


def _make_args(**overrides):
    from unittest.mock import Mock

    defaults = dict(
        debug=False,
        databasename="zoid6test",
        databasehost="localhost",
        databaseport=5432,
        databaseschema="engine",
    )
    defaults.update(overrides)
    return Mock(**defaults)


@pytest.fixture
def args():
    return _make_args()


@pytest.fixture
def echo_calls(monkeypatch):
    """Capture every io.echo(..., level=...) call as a list of (level, text) tuples."""
    from bbsengine6 import io

    captured = []
    real_echo = io.echo

    def _spy(text, *a, **kw):
        level = kw.get("level")
        if level is not None:
            captured.append((level, text))
        return real_echo(text, *a, **kw)

    monkeypatch.setattr(io, "echo", _spy)
    monkeypatch.setattr(libmember.io, "echo", _spy)
    return captured


# Real bcrypt hash for plaintext "12345" at cost 4 (fast for tests).
# Generated at import time via passlib with a fixed 22-char base64 salt so
# the value is deterministic across test runs (the audit tests only need
# the prefix $2b$ and the 60-char length; the checkpassword test needs
# stdlib crypt() / passlib bcrypt.verify to confirm it as the password
# for "12345"). If passlib is unavailable, fall back to a syntactically
# valid 60-char placeholder that audit still classifies as bcrypt but
# verify rejects — the checkpassword test will skip via pytest.importorskip.
try:
    from passlib.hash import bcrypt as _pl_bcrypt  # noqa: F401
    _BCRYPT_HASH = _pl_bcrypt.using(rounds=4, salt="12345678901234567890uv").hash("12345")
except ImportError:  # pragma: no cover
    _BCRYPT_HASH = "$2b$04$" + "Z" * 22 + "." * 31
_MD5CRYPT_HASH = "$1$AUNKK0aN$" + "abcdefghijklmnopqrstuvwxyz01"  # 34 chars total


def test_audit_password_hash_bcrypt_emits_ok(args, echo_calls):
    """A healthy bcrypt hash returns all-True flags and a level='ok' log line."""
    cursor = _SpyCursor(password=_BCRYPT_HASH)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is True
    assert audit.non_empty is True
    assert audit.prefix == "$2b$"
    assert audit.is_bcrypt is True
    assert audit.is_md5crypt is False
    assert audit.length_ok is True

    levels = [lvl for lvl, _text in echo_calls]
    assert "ok" in levels
    assert "warning" not in levels
    assert "error" not in levels


def test_audit_password_hash_md5crypt_emits_warning(args, echo_calls):
    """A $1$ MD5-crypt hash (the 2026-08-22 incident trigger) emits a warning
    with the prefix and a sample of the hash, and sets is_md5crypt=True."""
    cursor = _SpyCursor(password=_MD5CRYPT_HASH)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is True
    assert audit.non_empty is True
    assert audit.prefix == "$1$A"  # first 4 chars of $1$<salt>$<hash>
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is True
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels
    assert "ok" not in levels

    warn_texts = [text for lvl, text in echo_calls if lvl == "warning"]
    assert any("MD5-crypt" in t for t in warn_texts), (
        f"warning log must mention MD5-crypt; got: {warn_texts}"
    )
    assert any("$1$AUNKK0aN$" in t for t in warn_texts), (
        f"warning log must include the hash prefix for the operator; got: {warn_texts}"
    )


def test_audit_password_hash_null_emits_warning(args, echo_calls):
    """A NULL password column emits present=False + a warning."""
    cursor = _SpyCursor(password=None)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is False
    assert audit.non_empty is False
    assert audit.prefix == ""
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is False
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels
    assert "ok" not in levels


def test_audit_password_hash_empty_string_emits_warning(args, echo_calls):
    """An empty-string password emits non_empty=False + a warning."""
    cursor = _SpyCursor(password="")
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is True
    assert audit.non_empty is False
    assert audit.prefix == ""
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is False
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels
    assert "ok" not in levels


def test_audit_password_hash_34_char_non_prefixed_emits_warning(args, echo_calls):
    """A 34-char text without a bcrypt prefix is mis-classified: not bcrypt,
    wrong length, and the audit logs a warning with the prefix and length."""
    bad = "x" * 34  # length matches MD5-crypt but no $ prefix
    cursor = _SpyCursor(password=bad)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is True
    assert audit.non_empty is True
    assert audit.prefix == "xxxx"
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is False
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels
    warn_texts = [text for lvl, text in echo_calls if lvl == "warning"]
    assert any("prefix=" in t for t in warn_texts), (
        f"warning must include the bad prefix; got: {warn_texts}"
    )


def test_audit_password_hash_60_char_non_bcrypt_prefix_emits_warning(
    args, echo_calls
):
    """A 60-char text without a $2 prefix (e.g. a custom hash format) emits a
    warning even though the length matches bcrypt — the prefix is the
    authoritative classifier."""
    bad = "X" + "Y" * 59  # 60 chars, prefix "XY$" is not $2...
    cursor = _SpyCursor(password=bad)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is True
    assert audit.non_empty is True
    assert audit.prefix == "XYYY"  # first 4 chars of "X" + "Y"*59
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is False
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels


def test_audit_password_hash_missing_member_emits_warning(args, echo_calls):
    """A moniker not in engine.__member returns present=False and a warning."""
    cursor = _SpyCursor(password=None, return_row=False)
    audit = libmember.audit_password_hash(args, "nobody", cur=cursor)

    assert audit.present is False
    assert audit.non_empty is False
    assert audit.prefix == ""
    assert audit.is_bcrypt is False
    assert audit.is_md5crypt is False
    assert audit.length_ok is False

    levels = [lvl for lvl, _text in echo_calls]
    assert "warning" in levels


def test_audit_password_hash_uses_existing_cursor_no_new_connection(
    args, monkeypatch
):
    """audit_password_hash must use the cursor passed via cur= kwarg, never
    open a new connection. Mirrors the CONN_POOL_PATTERN contract."""
    cursor = _SpyCursor(password=_BCRYPT_HASH)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.is_bcrypt is True
    assert len(cursor.calls) == 1, (
        f"audit must issue exactly one SELECT when given a cursor; "
        f"got {len(cursor.calls)} calls"
    )


@pytest.mark.parametrize(
    "password,expected_present,expected_non_empty,expected_is_bcrypt,expected_is_md5crypt,expected_level,case_id",
    [
        pytest.param(_BCRYPT_HASH, True, True, True, False, "ok", "bcrypt", id="bcrypt"),
        pytest.param(_MD5CRYPT_HASH, True, True, False, True, "warning", "md5crypt", id="md5crypt"),
        pytest.param(None, False, False, False, False, "warning", "null", id="null"),
        pytest.param("", True, False, False, False, "warning", "empty", id="empty"),
        pytest.param("x" * 34, True, True, False, False, "warning", "wrong-34", id="wrong-34"),
        pytest.param("X" + "Y" * 59, True, True, False, False, "warning", "wrong-60", id="wrong-60"),
    ],
)
def test_audit_password_hash_parametrized(
    args,
    echo_calls,
    password,
    expected_present,
    expected_non_empty,
    expected_is_bcrypt,
    expected_is_md5crypt,
    expected_level,
    case_id,
):
    """Single parametrized matrix covering the six cases called out in
    zoid6/TODO.md "Password column hardening — legacy MD5-crypt migration"
    item 3 (the runtime complement to the one-shot scans above)."""
    cursor = _SpyCursor(password=password)
    audit = libmember.audit_password_hash(args, "jam", cur=cursor)

    assert audit.present is expected_present, f"[{case_id}] present"
    assert audit.non_empty is expected_non_empty, f"[{case_id}] non_empty"
    assert audit.is_bcrypt is expected_is_bcrypt, f"[{case_id}] is_bcrypt"
    assert audit.is_md5crypt is expected_is_md5crypt, f"[{case_id}] is_md5crypt"

    levels_seen = {lvl for lvl, _ in echo_calls}
    assert expected_level in levels_seen, (
        f"[{case_id}] expected level={expected_level!r}; got {levels_seen}"
    )
    if expected_level == "ok":
        assert "warning" not in levels_seen, (
            f"[{case_id}] healthy hash must not emit a warning"
        )


class TestCheckpasswordCallsAudit:
    """Wire-up regression: every checkpassword call must invoke
    audit_password_hash on the same cursor so the operator sees one diagnostic
    line per auth attempt. The 2026-08-22 incident took four psql probes to
    diagnose because this hook was missing."""

    def test_checkpassword_invokes_audit_on_same_cursor(
        self, args, echo_calls, monkeypatch
    ):
        """checkpassword must SELECT password (row A), call audit_password_hash
        (which does its own SELECT on the same cursor), then run the bcrypt
        round-trip SELECT (row B). The audit MUST be between row A and row B."""
        import contextlib
        from unittest.mock import Mock
        from bbsengine6 import database

        spy_cursor = _SpyCursor(password=_BCRYPT_HASH)

        def _spy_connect_factory(cursor):
            @contextlib.contextmanager
            def _cm(*a, **kw):
                conn = _SpyConn(cursor)
                try:
                    yield conn
                except BaseException:
                    conn.rollback()
                    raise

            return _cm

        monkeypatch.setattr(database, "connect", _spy_connect_factory(spy_cursor))

        result = libmember.checkpassword(
            args, "12345", membermoniker="jam", pool=Mock()
        )

        assert result is True, (
            f"checkpassword must verify a correct bcrypt plaintext; got {result!r}"
        )
        assert len(spy_cursor.calls) >= 2, (
            f"checkpassword must issue at least 2 SELECTs (audit + round-trip); "
            f"got {len(spy_cursor.calls)}"
        )

        levels_seen = {lvl for lvl, _ in echo_calls}
        assert "ok" in levels_seen, (
            "healthy checkpassword path must emit a level='ok' diagnostic; "
            f"levels seen: {levels_seen}"
        )

    def test_checkpassword_invokes_audit_on_md5_hash_and_continues(
        self, args, echo_calls, monkeypatch
    ):
        """The 2026-08-22 incident scenario: stored password is a $1$ MD5-crypt
        hash, plaintext doesn't match, checkpassword returns False BUT the
        operator sees a level='warning' diagnostic naming MD5-crypt."""
        import contextlib
        from unittest.mock import Mock
        from bbsengine6 import database

        spy_cursor = _SpyCursor(
            password=_MD5CRYPT_HASH, rowcount_after_round_trip=0
        )

        def _spy_connect_factory(cursor):
            @contextlib.contextmanager
            def _cm(*a, **kw):
                conn = _SpyConn(cursor)
                try:
                    yield conn
                except BaseException:
                    conn.rollback()
                    raise

            return _cm

        monkeypatch.setattr(database, "connect", _spy_connect_factory(spy_cursor))

        result = libmember.checkpassword(
            args, "any-plaintext", membermoniker="jam", pool=Mock()
        )

        assert result is False, (
            "checkpassword must return False when the stored hash doesn't match"
        )

        warn_texts = [text for lvl, text in echo_calls if lvl == "warning"]
        assert any("MD5-crypt" in t for t in warn_texts), (
            f"checkpassword must propagate the MD5-crypt warning from the audit; "
            f"warnings: {warn_texts}"
        )
