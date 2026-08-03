# password_hash.py
# Password hashing using scrypt (primary) and SHA-256 (legacy verification).
#
# Format produced by hash_password():
#   "$scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>"
# Legacy SHA-256 hashes (no prefix) are still verified by verify_password().
#
# scrypt parameters chosen as a sensible default for interactive login on
# modern hardware (n=2**14, r=8, p=1, dklen=32, ~16 MiB). Tunable via
# environment variables BBSENGINE_SCRYPT_N, _R, _P if a deployment needs
# to raise the cost factor (e.g. n=2**15 ~ 64 MiB).

import base64
import hashlib
import hmac
import os
from typing import Optional, Tuple


SCRYPT_PREFIX = "$scrypt$"
LEGACY_SHA256_LEN = 32  # raw bytes of a SHA-256 digest


def _get_scrypt_params() -> Tuple[int, int, int, int]:
    n = int(os.environ.get("BBSENGINE_SCRYPT_N", str(1 << 14)))
    r = int(os.environ.get("BBSENGINE_SCRYPT_R", "8"))
    p = int(os.environ.get("BBSENGINE_SCRYPT_P", "1"))
    dklen = 32
    return n, r, p, dklen


def generate_salt(length: int = 32) -> str:
    """Generate random salt for password hashing.

    Args:
        length: Salt length in bytes (default 32).

    Returns:
        Base64-encoded random salt.
    """
    if length < 16:
        raise ValueError("Salt must be at least 16 bytes")
    return base64.b64encode(os.urandom(length)).decode("utf-8")


def _scrypt_hash(plaintext: str, salt_bytes: bytes) -> str:
    n, r, p, dklen = _get_scrypt_params()
    digest = hashlib.scrypt(
        plaintext.encode("utf-8"),
        salt=salt_bytes,
        n=n,
        r=r,
        p=p,
        dklen=dklen,
    )
    return base64.b64encode(digest).decode("utf-8")


def _scrypt_verify(plaintext: str, hashed: str, salt_bytes: bytes) -> bool:
    try:
        computed = _scrypt_hash(plaintext, salt_bytes)
        return hmac.compare_digest(computed, hashed)
    except (ValueError, OSError):
        return False


def _legacy_sha256_hash(plaintext: str, salt_bytes: bytes) -> str:
    h = hashlib.sha256()
    h.update(salt_bytes)
    h.update(plaintext.encode("utf-8"))
    return base64.b64encode(h.digest()).decode("utf-8")


def hash_password(plaintext: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash a password using scrypt.

    Args:
        plaintext: Plaintext password (must be non-empty).
        salt: Optional base64-encoded salt. Generated if None.

    Returns:
        Tuple of (hashed, salt) where hashed carries an algorithm prefix
        so verify_password() can dispatch to the right routine.

    Raises:
        ValueError: If plaintext is empty or salt is malformed.
    """
    if not plaintext or not isinstance(plaintext, str):
        raise ValueError("Plaintext must be non-empty string")

    if salt is None:
        salt = generate_salt()

    try:
        salt_bytes = base64.b64decode(salt)
    except Exception as e:
        raise ValueError(f"Invalid base64 salt: {e}") from e
    if len(salt_bytes) < 16:
        raise ValueError(f"Salt must be at least 16 bytes, got {len(salt_bytes)}")

    n, r, p, dklen = _get_scrypt_params()
    digest_b64 = _scrypt_hash(plaintext, salt_bytes)
    hashed = f"{SCRYPT_PREFIX}{n}${r}${p}${salt}${digest_b64}"
    return hashed, salt


def verify_password(plaintext: str, hashed: str, salt: str) -> bool:
    """Verify plaintext against a stored hash + salt.

    Constant-time via hmac.compare_digest. Returns False (never raises)
    for any malformed input or unsupported algorithm.
    """
    if (
        not plaintext
        or not isinstance(plaintext, str)
        or not hashed
        or not isinstance(hashed, str)
        or not salt
        or not isinstance(salt, str)
    ):
        return False

    try:
        salt_bytes = base64.b64decode(salt)
    except Exception:
        return False

    if hashed.startswith(SCRYPT_PREFIX):
        try:
            rest = hashed[len(SCRYPT_PREFIX):]
            n_s, r_s, p_s, salt_b64, digest_b64 = rest.split("$", 4)
            if base64.b64decode(salt_b64) != salt_bytes:
                # Salt in payload must match passed salt.
                return False
            n = int(n_s)
            r = int(r_s)
            p = int(p_s)
            computed = base64.b64encode(
                hashlib.scrypt(
                    plaintext.encode("utf-8"),
                    salt=salt_bytes,
                    n=n,
                    r=r,
                    p=p,
                    dklen=32,
                )
            ).decode("utf-8")
            return hmac.compare_digest(computed, digest_b64)
        except (ValueError, OSError, AttributeError, base64.binascii.Error):
            return False

    # Legacy: SHA-256(salt || plaintext), base64 encoded.
    try:
        computed = _legacy_sha256_hash(plaintext, salt_bytes)
        return hmac.compare_digest(computed, hashed)
    except Exception:
        return False


def is_hashed_password(value: str) -> bool:
    """Heuristic check: does *value* look like one of our password hashes?"""
    if not isinstance(value, str) or not value:
        return False
    if value.startswith(SCRYPT_PREFIX):
        return True
    try:
        decoded = base64.b64decode(value, validate=True)
        return len(decoded) == LEGACY_SHA256_LEN
    except Exception:
        return False


__all__ = [
    "generate_salt",
    "hash_password",
    "verify_password",
    "is_hashed_password",
]
