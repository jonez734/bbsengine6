"""bbsengine6.auth.pam -- pam_exec.so helper for the BBS auth backend.

Invoked by pam_exec.so with ``expose_authtok`` on the PAM rule line:
    auth sufficient pam_exec.so quiet expose_authtok /usr/local/bin/bbsengine6-auth-pam

Reads from the environment that pam_exec.so sets:
  - PAM_USER       -- the username
  - PAM_SERVICE    -- the service name (e.g. 'imap' for Cyrus auxprop-pam,
                      'dovecot' for the auth-system passdb)
  - PAM_TYPE       -- 'auth' (this helper runs on the auth stack) or
                      'account'/'session'/'password' (pass-through with
                      exit 0; the BBS gate is enforced in 'auth')
  - PAM_AUTHTOK    -- the plaintext password; only present when
                      expose_authtok is on the rule line

Calls ``bbsengine6.auth.verify.verify_member`` for the actual decision.
The password env var is read and immediately scrubbed
(os.environ.pop) before any other code can see it. See README.md
"Security model" for the threat model and mitigations.

Exit codes:
  0 -- auth success (PAM_TYPE=auth) or pass-through (other types)
  1 -- auth failure or missing PAM_USER/PAM_AUTHTOK
  2 -- DB / setup error (treated as transient by the PAM stack)
"""
from __future__ import annotations

import os
import sys

from bbsengine6.auth.cli import _log_outcome, _make_logger
from bbsengine6.auth.verify import verify_member


_LOG = _make_logger("bbsengine6.auth.pam")


def _read_and_scrub_password() -> str | None:
    """Read PAM_AUTHTOK from the env and pop it. Returns None if unset."""
    pw = os.environ.get("PAM_AUTHTOK")
    if pw is None:
        return None
    # The scrub. After this line, no code in this process can read
    # the password from the environment. The window is microseconds.
    os.environ.pop("PAM_AUTHTOK", None)
    return pw


def main(argv: list[str] | None = None) -> int:
    # PAM 'account' is a separate stack (no auth check needed for
    # account validity on this path; the BBS gate is checked in
    # 'auth'). Pass-through with exit 0.
    pam_type = os.environ.get("PAM_TYPE", "auth")
    if pam_type != "auth":
        return 0

    user = os.environ.get("PAM_USER", "").strip()
    if not user:
        _log_outcome(_LOG, user="", outcome="missing-pam-user")
        return 1

    password = _read_and_scrub_password()
    if password is None:
        _log_outcome(_LOG, user=user, outcome="missing-authtok")
        return 1

    try:
        ok, outcome = verify_member(user, password)
    except Exception as exc:
        _LOG.error(
            "db-error user=%s service=%s err=%s",
            user,
            os.environ.get("PAM_SERVICE", ""),
            exc.__class__.__name__,
        )
        return 2

    _log_outcome(
        _LOG,
        user=user,
        outcome=outcome,
        service=os.environ.get("PAM_SERVICE", ""),
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
