"""bbsengine6.auth.cli -- shared CLI helpers for the auth entry points.

Used by:
  - bbsengine6.auth.dovecot (Dovecot checkpassword protocol on stdin/stdout)
  - bbsengine6.auth.pam (PAM pam_exec.so helper, reads PAM env)

The two entry points handle different protocols but share the outcome-
logging helper (so a single log line format is produced regardless of
which entry point is calling verify_member).
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def _log_outcome(
    log: logging.Logger,
    *,
    user: str,
    outcome: str,
    **extra: object,
) -> None:
    """Log an auth outcome without ever including the password.

    outcome values (canonical, used by tests):
      ok, no-user, not-approved, sasl-disabled, mailbox-disabled,
      sasl-expired, wrong-password, db-error, missing-pam-user,
      missing-password, missing-authtok, account-type, mail-no-user.
    """
    fields = {"user": user, "outcome": outcome, **extra}
    log.info(
        "auth %s",
        " ".join(f"{k}={v}" for k, v in fields.items() if v is not None),
    )


def _read_checkpassword_stdin() -> Optional[str]:
    """Read the password from a Dovecot checkpassword stdin.

    Protocol: <password>\\0<userinfo>\\0<rest...>
    We do not trust userinfo here; the username comes from AUTH_USER env.
    """
    data = sys.stdin.buffer.read(4096)
    if not data:
        return None
    return data.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def _make_logger(name: str) -> logging.Logger:
    """Build the standard auth logger that writes to stderr (journald).

    Honors BBSENGINE6_AUTH_LOG (DEBUG/INFO/WARNING/ERROR).
    """
    log = logging.getLogger(name)
    if not log.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(name)s %(levelname)s %(message)s")
        )
        log.addHandler(handler)
    log.setLevel(os.environ.get("BBSENGINE6_AUTH_LOG", "INFO").upper())
    return log
