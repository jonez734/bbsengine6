"""
Tests for bbsengine6.password — bcrypt implementation matching
the PHP bbsengine6\\password namespace API.

Covers:
- hash_password() produces a bcrypt hash ($2b$06$..., length 60)
- verify_password() round-trips successfully
- verify_password() rejects wrong passwords (constant-time via passlib)
- verify_password() accepts legacy MD5-crypt $1$ hashes (PHP parity)
- verify_password() never raises on malformed input
- hash_password() rejects empty plaintext
- is_healthy_hash() detects $2[abxy]$ at length 60
- is_healthy_hash() rejects MD5-crypt, empty, null, wrong length
- needs_rehash() inverts is_healthy_hash()
- classify_hash() returns the right label for each input class
- BBSENGINE_BCRYPT_ROUNDS env var is honoured (with range guard)
- Two hashes of the same plaintext differ (fresh salt per call)
- UTF-8 plaintext round-trips
"""

import pytest

from bbsengine6.password import (
    BCRYPT_HASH_LENGTH,
    BCRYPT_PREFIX_RE,
    MD5CRYPT_PREFIX_RE,
    classify_hash,
    hash_password,
    is_healthy_hash,
    needs_rehash,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_produces_bcrypt_prefix():
    h = hash_password("hunter2")
    assert h.startswith("$2b$06$"), f"hash should be $2b$06$-prefixed, got: {h[:10]!r}"
    assert len(h) == BCRYPT_HASH_LENGTH == 60


def test_hash_password_round_trip():
    plaintext = "correct horse battery staple"
    h = hash_password(plaintext)
    assert verify_password(plaintext, h) is True


def test_verify_password_rejects_wrong_password():
    h = hash_password("right")
    assert verify_password("wrong", h) is False


def test_verify_password_empty_inputs_return_false():
    h = hash_password("anything")
    assert verify_password("", h) is False
    assert verify_password(None, h) is False  # type: ignore[arg-type]
    assert verify_password("anything", "") is False
    assert verify_password("anything", None) is False  # type: ignore[arg-type]


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError):
        hash_password("")
    with pytest.raises(ValueError):
        hash_password(None)  # type: ignore[arg-type]


def test_hash_password_rejects_non_string():
    with pytest.raises(ValueError):
        hash_password(12345)  # type: ignore[arg-type]


def test_two_hashes_with_same_plaintext_differ():
    """Each call to hash_password should generate a fresh salt."""
    h1 = hash_password("same input")
    h2 = hash_password("same input")
    assert h1 != h2


def test_verify_password_rejects_legacy_md5crypt():
    """Python/ passlib bcrypt.verify only accepts bcrypt hashes.

    PHP's password_verify() accepts legacy $1$ MD5-crypt as a side
    effect (the underlying crypt() function supports multiple
    algorithms); passlib's bcrypt.verify is bcrypt-only and returns
    False for $1$. The Python-side equivalent of the opportunistic-
    rehash path is therefore the SQL round-trip in
    bbsengine6.member.checkpassword (``where password = crypt(%s,
    password)``), which still recognises $1$ via PG's crypt().

    After the Python member.checkpassword drops its own DB round-trip
    (future work, mirroring the PHP rewrite in this commit series),
    the legacy-rehash path will need an explicit
    ``crypt($plaintext, $stored)`` Python check before falling
    through to ``password.verify_password``.
    """
    legacy = "$1$abcdefgh$irWbblnpmw.5z7wgBnprh0"
    assert verify_password("test", legacy) is False
    assert verify_password("WRONG", legacy) is False


def test_verify_password_malformed_hash_returns_false_not_raises():
    assert verify_password("anything", "not-a-hash") is False
    assert verify_password("anything", "$") is False
    assert verify_password("anything", "$2y$06$too-short") is False
    assert verify_password("anything", "$2y$06$" + "x" * 100) is False
    assert verify_password("anything", "$9$" + "x" * 57) is False


def test_is_healthy_hash_accepts_bcrypt_variants():
    valid = [
        "$2a$06$" + "a" * 53,
        "$2b$06$" + "b" * 53,
        "$2x$06$" + "c" * 53,
        "$2y$06$" + "d" * 53,
    ]
    for h in valid:
        assert is_healthy_hash(h) is True, f"rejected healthy hash: {h}"


def test_is_healthy_hash_rejects_md5crypt_empty_null_wrong_length():
    bad = [
        "$1$abc$" + "x" * 22,
        "",
        None,
        "$2y$06$short",
        "$5$" + "x" * 57,
        "plaintext-password",
    ]
    for h in bad:
        assert is_healthy_hash(h) is False, f"accepted unhealthy value: {h!r}"


def test_needs_rehash_inverts_is_healthy_hash():
    cases = [
        ("$2y$06$" + "a" * 53, False),
        ("$1$abc$" + "x" * 22, True),
        ("", True),
        (None, True),
        ("$2y$06$short", True),
        ("plaintext", True),
    ]
    for stored, want in cases:
        got = needs_rehash(stored)
        assert got == want, f"needs_rehash({stored!r}) = {got} want {want}"


def test_classify_hash_labels():
    cases = [
        (None, "null"),
        ("", "empty"),
        ("$2y$06$" + "a" * 53, "bcrypt"),
        ("$2b$06$" + "b" * 53, "bcrypt"),
        ("$1$abc$" + "x" * 22, "md5crypt"),
        ("plaintext", "other"),
        ("$5$short", "other"),
    ]
    for stored, want in cases:
        got = classify_hash(stored)
        assert got == want, f"classify_hash({stored!r}) = {got!r} want {want!r}"


def test_bcrypt_prefix_re_matches_all_bcrypt_variants():
    for variant in ("$2a$", "$2b$", "$2x$", "$2y$"):
        assert BCRYPT_PREFIX_RE.match(variant + "06$xxxx") is not None
    for non_variant in ("$1$", "$5$", "$6$", "$2z$", "plain"):
        assert BCRYPT_PREFIX_RE.match(non_variant + "06$xxxx") is None


def test_md5crypt_prefix_re_matches_legacy_only():
    assert MD5CRYPT_PREFIX_RE.match("$1$abcdefgh$xxx") is not None
    assert MD5CRYPT_PREFIX_RE.match("$2y$06$xxx") is None
    assert MD5CRYPT_PREFIX_RE.match("plain") is None


def test_bcrypt_rounds_env_override(monkeypatch):
    monkeypatch.setenv("BBSENGINE_BCRYPT_ROUNDS", "8")
    h = hash_password("env-test")
    assert h.startswith("$2b$08$"), f"hash should reflect BBSENGINE_BCRYPT_ROUNDS=8, got: {h[:10]!r}"


def test_bcrypt_rounds_env_out_of_range(monkeypatch):
    monkeypatch.setenv("BBSENGINE_BCRYPT_ROUNDS", "20")
    with pytest.raises(ValueError, match="out of range"):
        hash_password("x")


def test_utf8_plaintext_round_trips():
    pw = "pâsswörd-😀-12345"
    h = hash_password(pw)
    assert verify_password(pw, h) is True
    assert verify_password(pw + "x", h) is False
