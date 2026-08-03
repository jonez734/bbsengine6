"""
Regression tests for Phase 2 password_hash.py hardening.

Covers:
- hash_password() produces scrypt-prefixed format ($scrypt$n$r$p$salt$digest)
- verify_password() round-trips successfully
- verify_password() rejects wrong passwords (constant-time via hmac)
- verify_password() still verifies legacy SHA-256 hashes (back-compat)
- verify_password() never raises on malformed input
- hash_password() rejects empty plaintext
- is_hashed_password() detects both new and legacy formats
"""

import pytest

from bbsengine6.password_hash import (
    SCRYPT_PREFIX,
    generate_salt,
    hash_password,
    is_hashed_password,
    verify_password,
)

pytestmark = pytest.mark.unit


def test_hash_password_produces_scrypt_prefix():
    hashed, salt = hash_password("hunter2", salt=generate_salt())
    assert hashed.startswith(SCRYPT_PREFIX), (
        f"hash should be scrypt-prefixed, got: {hashed[:40]!r}"
    )


def test_hash_password_round_trip():
    plaintext = "correct horse battery staple"
    hashed, salt = hash_password(plaintext)
    assert verify_password(plaintext, hashed, salt) is True


def test_verify_password_rejects_wrong_password():
    hashed, salt = hash_password("right")
    assert verify_password("wrong", hashed, salt) is False


def test_verify_password_empty_plaintext_returns_false():
    hashed, salt = hash_password("anything")
    assert verify_password("", hashed, salt) is False
    assert verify_password(None, hashed, salt) is False  # type: ignore[arg-type]


def test_hash_password_rejects_empty():
    with pytest.raises(ValueError):
        hash_password("")
    with pytest.raises(ValueError):
        hash_password(None)  # type: ignore[arg-type]


def test_hash_password_rejects_short_salt():
    import base64

    too_short = base64.b64encode(b"short").decode("utf-8")
    with pytest.raises(ValueError):
        hash_password("anything", salt=too_short)


def test_verify_legacy_sha256_still_works():
    """Pre-existing SHA-256(salt||plaintext), base64 hashes must still verify.

    The DB may contain hashes produced by the old code; verify_password
    must accept them so we don't orphan member accounts during rollout.
    """
    import base64
    import hashlib

    plaintext = "legacy"
    salt_bytes = b"\x00" * 16
    salt_b64 = base64.b64encode(salt_bytes).decode("utf-8")
    h = hashlib.sha256()
    h.update(salt_bytes)
    h.update(plaintext.encode("utf-8"))
    legacy_hash = base64.b64encode(h.digest()).decode("utf-8")

    assert verify_password(plaintext, legacy_hash, salt_b64) is True
    assert verify_password("wrong", legacy_hash, salt_b64) is False


def test_verify_malformed_hash_returns_false_not_raises():
    assert verify_password("anything", "not-base64-$$$$", "salt") is False
    assert verify_password("anything", "", "salt") is False
    assert verify_password("anything", "$scrypt$", "salt") is False
    assert verify_password("anything", "$scrypt$bad$bad$bad$bad$bad", "salt") is False


def test_is_hashed_password_detection():
    hashed, _ = hash_password("anything")
    assert is_hashed_password(hashed) is True
    assert is_hashed_password("not-a-hash") is False
    assert is_hashed_password("") is False
    assert is_hashed_password(None) is False  # type: ignore[arg-type]


def test_two_hashes_with_same_plaintext_differ():
    """Each call to hash_password should generate a fresh salt."""
    plaintext = "same input"
    h1, _ = hash_password(plaintext)
    h2, _ = hash_password(plaintext)
    assert h1 != h2
