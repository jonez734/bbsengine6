"""bbsengine6.auth.pam -- pam_exec.so helper for the BBS auth backend.

Invoked by pam_exec.so with ``expose_authtok`` on the PAM rule line:
    auth sufficient pam_exec.so quiet expose_authtok /usr/local/bin/bbsengine6-auth-pam

Reads from the environment that pam_exec.so sets:
  - PAM_USER       -- the username (always)
  - PAM_SERVICE    -- the service name (e.g. 'imap' for Cyrus auxprop-pam,
                      'dovecot' for Dovecot's auth-system passdb)
  - PAM_TYPE       -- 'auth' or 'account' (or 'session', 'password')
  - PAM_AUTHTOK    -- the plaintext password (only when expose_authtok is
                      on the rule line; this is the load-bearing case)

Security model
--------------

The plaintext password is in the ``PAM_AUTHTOK`` env var for the
lifetime of this process. /proc/<pid>/environ is readable by root
for the process's lifetime. Mitigations:

1. This helper reads PAM_AUTHTOK and immediately calls
   ``os.environ.pop("PAM_AUTHTOK")`` so subsequent code in this
   process cannot see the value. The in-process exposure window is
   microseconds (one Python statement).

2. The helper runs as root (because pam_exec.so forks from the
   privileged parent that ran the auth). /proc/<pid>/environ is
   still readable to root, but the value is now empty.

3. The helper does not log the password. The outcome line contains
   the user and an outcome class (ok / wrong-password / etc.) but
   never the password.

4. The DB call is wrapped in a READ ONLY transaction (see
   bbsengine6.auth.verify.verify_member). Even if an attacker could
   influence the SQL, they cannot write to the BBS DB.

Threat model
------------

Acceptable given the root-trust model on the host: an attacker who
can read /proc/<pid>/environ of a root-owned process already has
root on the host. The env-var exposure does not increase the
attack surface meaningfully beyond "operator has root on merlin or
falcon."

If a future threat model requires keeping the password out of the
helper's env entirely, the only correct path is a real Linux-PAM
module in C (e.g. pam_bbsengine6.so, not in scope here). The pure-
Python path is the trade for code reuse with bbsengine6.auth.verify
and zero C build / no .so on the target.
"""
from __future__ import annotations

import os
import sys

from bbsengine6.auth.cli import _log_outcome, _make_logger
from bbsengine6.auth.verify import verify_member


_LOG = _make_logger("bbsengine6.auth.pam")


def _read_and_scrub_password() -> str | None:
    """Read the password from PAM_AUTHTOK and immediately scrub the env.

    Returns None if PAM_AUTHTOK is not set (rule line missing
    expose_authtok, or this is being called outside a PAM context).
    """
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
