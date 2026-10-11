"""bbsengine6.auth.verify -- read-only BBS auth gate.

The single source of truth for the BBS auth decision. Used by:
  - bbsengine6-auth-checkpassword (Dovecot passdb checkpassword)
  - bbsengine6-auth-pam (Cyrus auxprop-pam, SSH, sudo, future)

Dispatches on '@' in the username:
  - user contains '@'  -> per-mailbox path (postoffice.mailbox_password)
  - user has no '@'    -> per-user path    (engine.__member.password)

The per-mailbox path is what Cyrus uses when a member authenticates to
a specific mailbox address (e.g. "alice@bbsengine.org"). The per-user
path is what the BBS web login uses, and what SSH/sudo would use.

Both paths check:
  1. engine.__member row exists with approved = true
  2. engine.__member.accountexpires IS NULL OR > now()
  3. The relevant password column verifies against the supplied plaintext
     (crypt.crypt() for $1$/$5$/$6$/$2[aby]$; bcrypt.checkpw fallback)

The whole thing runs in a single READ ONLY transaction so a future bug
cannot accidentally write to the DB.
"""
from __future__ import annotations

import argparse
import crypt
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import bcrypt
import psycopg
from psycopg.rows import dict_row

from bbsengine6 import database


_LOG = logging.getLogger("bbsengine6.auth.verify")


def _build_args(
    *,
    dbname: Optional[str] = None,
    dbhost: Optional[str] = None,
    dbport: Optional[int] = None,
    dbuser: Optional[str] = None,
) -> argparse.Namespace:
    """Build a minimal args namespace for database.getpool().

    The DSN chain (database.make_dsn) reads from args + BBSENGINE6_DB*
    env vars + kwargs. Tests pass everything explicitly; production
    relies on the env vars set by /etc/bbsengine6/auth.conf (via
    bbsengine6.auth.cli for the helper entry points).
    """
    return argparse.Namespace(
        databasename=dbname,
        databasehost=dbhost,
        databaseport=dbport,
        databaseuser=dbuser,
        # databasepassword is read from BBSENGINE6_DBPASSWORD env var
        # by database._resolve_db_settings, so we don't need to set it
        # here.
    )


def _verify_hash(plaintext: str, stored_hash: str) -> bool:
    """Verify plaintext against stored_hash.

    Algorithm coverage (in priority order):
      1. Python stdlib crypt.crypt(plaintext, stored_hash) -- handles
         every crypt(3) variant glibc supports: $1$ MD5-crypt,
         $5$ SHA-256-crypt, $6$ SHA-512-crypt, and the $2[aby]$ bcrypt
         family. Returns None if the algorithm is not supported.
      2. bcrypt.checkpw -- bcrypt-specific fallback for platforms
         where stdlib crypt lacks bcrypt support.
    """
    if not stored_hash or not plaintext:
        return False
    try:
        result = crypt.crypt(plaintext, stored_hash)
    except (TypeError, ValueError):
        result = None
    if result is not None:
        return result == stored_hash
    # Fallback: bcrypt
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"),
                              stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _is_past(expires_at: Any, now: datetime) -> bool:
    """Return True iff expires_at is a non-NULL timestamp strictly before now."""
    if expires_at is None:
        return False
    if isinstance(expires_at, str):
        # Defensive: psycopg returns timestamptz as datetime, but a custom
        # row factory or a tests fixture might return a string.
        try:
            expires_at = datetime.fromisoformat(expires_at)
        except ValueError:
            return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < now


def _dispatch(username: str) -> str:
    """Return 'mailbox' if username contains '@', else 'user'."""
    return "mailbox" if "@" in username else "user"


def _verify_per_user(
    cur: psycopg.Cursor,
    username: str,
    plaintext: str,
    now: datetime,
) -> tuple[bool, str]:
    """Per-user path. Returns (ok, outcome)."""
    cur.execute(
        """
        SELECT password, approved, accountexpires
          FROM engine.__member
         WHERE moniker = %s
        """,
        (username,),
    )
    row = cur.fetchone()
    if row is None:
        return False, "no-user"
    if not row["approved"]:
        return False, "not-approved"
    if _is_past(row["accountexpires"], now):
        return False, "sasl-expired"
    stored = row["password"]
    if not stored:
        return False, "wrong-password"
    if not _verify_hash(plaintext, stored):
        return False, "wrong-password"
    return True, "ok"


def _verify_per_mailbox(
    cur: psycopg.Cursor,
    address: str,
    plaintext: str,
    now: datetime,
) -> tuple[bool, str]:
    """Per-mailbox path. Returns (ok, outcome)."""
    cur.execute(
        """
        SELECT mp.password AS pw,
               m.approved AS m_approved,
               m.accountexpires AS m_expires,
               mp.enabled AS mp_enabled,
               mb.enabled AS mb_enabled
          FROM postoffice.mailbox_password mp
          JOIN engine.__member m  ON m.id  = mp.memberid
          JOIN postoffice.mailbox mb ON mb.address = mp.address
         WHERE mp.address = %s
           AND mp.kind = 'inbound'
        """,
        (address,),
    )
    row = cur.fetchone()
    if row is None:
        return False, "mail-no-user"
    if not row["m_approved"]:
        return False, "not-approved"
    if _is_past(row["m_expires"], now):
        return False, "sasl-expired"
    if not row["mp_enabled"]:
        return False, "mailbox-disabled"
    if not row["mb_enabled"]:
        return False, "mailbox-disabled"
    stored = row["pw"]
    if not stored:
        return False, "wrong-password"
    if not _verify_hash(plaintext, stored):
        return False, "wrong-password"
    return True, "ok"


def verify_member(
    username: str,
    password: str,
    *,
    args: Optional[argparse.Namespace] = None,
    pool: Any = None,
    now: Optional[datetime] = None,
) -> tuple[bool, str]:
    """Read-only BBS auth. Dispatches on '@' in username.

    Returns (ok, outcome) where outcome is a short canonical string
    ("ok", "no-user", "not-approved", "mailbox-disabled",
    "sasl-expired", "wrong-password", "db-error", "mail-no-user").

    Opens a READ ONLY transaction on the supplied pool (or one acquired
    from bbsengine6.database via args). Never writes.

    CONN_POOL_PATTERN:
      1. pool= -- use caller's existing pool
      2. args= -- build/cache pool via database.getpool(args)
      3. Default args() -- reads BBSENGINE6_DB* env vars
    """
    if not username or not password:
        return False, "wrong-password"

    if now is None:
        now = datetime.now(timezone.utc)

    if args is None:
        args = _build_args()
    if pool is None:
        pool = database.getpool(args)

    path = _dispatch(username)

    conn = pool.getconn()
    try:
        conn.autocommit = False
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("BEGIN READ ONLY")
            try:
                if path == "mailbox":
                    ok, outcome = _verify_per_mailbox(cur, username, password, now)
                else:
                    ok, outcome = _verify_per_user(cur, username, password, now)
            finally:
                try:
                    cur.execute("END")
                except psycopg.Error:
                    pass
        return ok, outcome
    except psycopg.Error as exc:
        _LOG.error("db-error path=%s err=%s", path, exc.__class__.__name__)
        return False, "db-error"
    finally:
        try:
            conn.rollback()
        except psycopg.Error:
            pass
        pool.putconn(conn)


__all__ = ["verify_member", "_verify_hash", "_dispatch"]
