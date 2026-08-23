# password_hash.py
# Member-login password hashing — bcrypt (single source of truth).
#
# Mirrors bbsengine6\\password\\libpassword.php on the PHP side. Both
# expose the same five-function API surface and both produce a
# $2[aby]$06$ bcrypt hash of length 60 so the chk_member_password_
# bcrypt CHECK constraint and the per-auth audit hook accept the
# output without further translation.
#
# Format produced by hash_password():
#   "$2b$06$<22-char salt><31-char digest>"  (length 60)
#
# Constant names match the PHP-side bbsengine6\\password exactly:
#
#   BBSENGINE_BCRYPT_COST, BCRYPT_PREFIX_REGEX, BCRYPT_HASH_LENGTH,
#   LEGACY_MD5_PREFIX_REGEX
#
# Cost factor matches:
#   - bbsengine6\\password\\BBSENGINE_BCRYPT_COST (PHP, defined = 6)
#   - PostgreSQL gen_salt('bf') default (PG, = 6)
#   - the previous util._BCRYPT_ROUNDS = 6 (Python, now moved here)
#
# Overridable via env var BBSENGINE_BCRYPT_ROUNDS. Bumping this
# requires a one-shot rehash of every engine.__member.password row;
# the needs_rehash() helper below drives that migration on the next
# successful login (mirrors PHP's opportunistic-rehash path).
#
# Cross-platform note: PHP password_hash() emits $2y$, pyca bcrypt
# emits $2b$, PG crypt(plaintext, stored) only recognises $2a$ (gen_salt
# output). Since verification is local on each platform after
# eliminating the DB round-trip, the cross-platform prefix drift is
# harmless — the integration test (test_php_password_round_trip.php
# + test_password_hash_bcrypt.py) pins the behaviour so any future
# regression that reintroduces the DB round-trip catches the
# mismatch immediately.
#
# @since 20260823 — re-pointed at bcrypt to match the PHP version.
#                  Replaces the prior scrypt + legacy SHA-256
#                  implementation that was effectively dead code
#                  (no production callers; util.encryptpassword was
#                  using bcrypt directly with the same cost factor).

import bcrypt
import os
import re
from typing import Optional


BCRYPT_PREFIX_REGEX = re.compile(r"^\$2[abxy]\$")
# Backward-compat alias for the previous (Python-only) suffix; the
# canonical name now matches the PHP-side
# bbsengine6\\password\BCRYPT_PREFIX_REGEX.
BCRYPT_PREFIX_RE = BCRYPT_PREFIX_REGEX
LEGACY_MD5_PREFIX_REGEX = re.compile(r"^\$1\$")
# Backward-compat alias for the previous name. The canonical name
# matches the PHP-side bbsengine6\\password\LEGACY_MD5_PREFIX_REGEX.
MD5CRYPT_PREFIX_RE = LEGACY_MD5_PREFIX_REGEX
BCRYPT_HASH_LENGTH = 60


def _get_bcrypt_rounds() -> int:
    """Read the cost-factor env var with a 6-round default.

    Canonical name is BBSENGINE_BCRYPT_COST (matches the PHP-side
    bbsengine6\\password constant). BBSENGINE_BCRYPT_ROUNDS is
    accepted as a deprecated alias for one release cycle to give
    operators time to update deploy configs. Set this to 10+ in
    production deployments that can afford the extra ~100ms per
    login.
    """
    raw = os.environ.get("BBSENGINE_BCRYPT_COST")
    if raw is None:
        raw = os.environ.get("BBSENGINE_BCRYPT_ROUNDS", "6")
    try:
        rounds = int(raw)
    except ValueError:
        rounds = 6
    if rounds < 4 or rounds > 15:
        raise ValueError(
            f"BBSENGINE_BCRYPT_ROUNDS={rounds} out of range [4, 15]"
        )
    return rounds


def hash_password(plaintext: str) -> str:
    """Return a fresh bcrypt hash of *plaintext*.

    No database round-trip. Uses ``bcrypt.hashpw`` (pyca) with a
    fresh ``bcrypt.gensalt`` at the cost factor from
    ``BBSENGINE_BCRYPT_COST`` (default 6). Returns a ``$2b$06$...``
    string of length 60 — verifiable by ``verify_password()`` and
    accepted by the ``chk_member_password_bcrypt`` CHECK constraint
    (``^\\$2[abxy]\\$``, len 60).

    Raises:
        ValueError: If plaintext is empty / None.

    Args:
        plaintext: Plaintext password (must be non-empty string).

    Returns:
        Bcrypt hash, length 60, prefix ``$2b$``.

    Example:
        >>> h = hash_password("hunter2")
        >>> len(h) == 60 and h.startswith("$2b$06$")
        True
    """
    if not plaintext or not isinstance(plaintext, str):
        raise ValueError("Plaintext must be non-empty string")
    salt = bcrypt.gensalt(rounds=_get_bcrypt_rounds(), prefix=b"2b")
    return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("ascii")


def verify_password(plaintext: str, stored: str) -> bool:
    """Return True iff *plaintext* matches *stored*.

    Constant-time via bcrypt.checkpw (uses hmac.compare_digest internally).
    digest internally). Returns False (never raises) on empty,
    None, or otherwise malformed input so callers can use a single
    truthiness check.

    Args:
        plaintext: Plaintext password from the form.
        stored:    Value from engine.__member.password.

    Returns:
        True iff the plaintext verifies against the stored hash.
    """
    if not plaintext or not isinstance(plaintext, str):
        return False
    if not stored or not isinstance(stored, str):
        return False
    try:
        return bcrypt.checkpw(
            plaintext.encode("utf-8"), stored.encode("ascii")
        )
    except (ValueError, TypeError):
        return False


def is_healthy_hash(stored: Optional[str]) -> bool:
    """Return True iff *stored* is structurally a valid bcrypt hash.

    Accepts ``$2a$``, ``$2b$``, ``$2x$``, ``$2y$`` prefixes at
    length 60. Mirrors bbsengine6\\password\\is_healthy_hash on the
    PHP side and matches the predicate enforced by the
    ``chk_member_password_bcrypt`` CHECK constraint.

    Args:
        stored: Value from engine.__member.password (or None).

    Returns:
        True iff structurally a healthy bcrypt hash.
    """
    if stored is None or stored == "":
        return False
    if len(stored) != BCRYPT_HASH_LENGTH:
        return False
    return bool(BCRYPT_PREFIX_REGEX.match(stored))


def needs_rehash(stored: Optional[str]) -> bool:
    """Return True iff a successful verify should re-write the row.

    Inverse of is_healthy_hash. True for any non-bcrypt value
    (``$1$`` MD5-crypt, empty, wrong length, wrong prefix, NULL).
    Drives the opportunistic-rehash path in
    bbsengine6\\member\\lib\\checkpassword (PHP) and
    bbsengine6.member.checkpassword (Python).

    Args:
        stored: Value from engine.__member.password (or None).

    Returns:
        True iff the row should be rewritten on next successful
        verify.
    """
    return not is_healthy_hash(stored)


def classify_hash(stored: Optional[str]) -> str:
    """Return a one-word label for *stored* for diagnostic logging.

    Returns one of:
      - "bcrypt":   structurally valid ``$2[abxy]$`` hash at length 60
      - "md5crypt": ``$1$...`` legacy MD5-crypt hash
      - "other":    any other non-empty string
      - "empty":    empty string
      - "null":     Python None

    Mirrors bbsengine6\\password\\classify_hash on the PHP side and
    is used by bbsengine6.member.audit_password_hash's diagnostic
    log lines so the operator can see the failure mode at a glance.

    Args:
        stored: Value from engine.__member.password (or None).

    Returns:
        Label string.
    """
    if stored is None:
        return "null"
    if stored == "":
        return "empty"
    if BCRYPT_PREFIX_REGEX.match(stored):
        return "bcrypt"
    if MD5CRYPT_PREFIX_RE.match(stored):
        return "md5crypt"
    return "other"


__all__ = [
    "BCRYPT_PREFIX_REGEX",
    "LEGACY_MD5_PREFIX_REGEX",
    "BCRYPT_HASH_LENGTH",
    "BBSENGINE_BCRYPT_COST",
    "hash_password",
    "verify_password",
    "is_healthy_hash",
    "needs_rehash",
    "classify_hash",
]
