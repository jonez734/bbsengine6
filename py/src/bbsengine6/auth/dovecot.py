"""bbsengine6.auth.dovecot -- Dovecot checkpassword protocol entry point.

Implements the [Dovecot checkpassword protocol][1] used by
Dovecot's ``passdb checkpassword`` driver.

Stdin format (one read, capped at 4096 bytes):
    <password>\\0<userinfo>\\0<rest...>

We do NOT trust the userinfo field for the username. The username
comes from the AUTH_USER env var that Dovecot sets when invoking
the script. (This matches the Dovecot wiki's "Standard
checkpassword" guidance.)

On success, print the userdb-style fields to stdout, flush, exit 0:
    home=<mail_home>
    mail=<mail_location>
    uid=<vmail_uid>
    gid=<vmail_gid>
    userdb_home=<mail_home>
    userdb_mail=<mail_location>
    userdb_uid=<vmail_uid>
    userdb_gid=<vmail_gid>

On auth failure: print nothing, exit 1.
On DB / setup error: print nothing, exit 2 (Dovecot treats this as
a transient error and may retry).

[1]: https://doc.dovecot.org/configuration_manual/authentication/checkpassword/

The mail_home/mail_location/uid/gid defaults match the existing
zoidlan/merlin/jammy/dovecot/local.conf values so the existing
ACL/quota/sieve setup keeps working unchanged. They can be
overridden via env vars (BBSENGINE6_AUTH_MAIL_HOME etc.) for
operators who run a different layout.
"""
from __future__ import annotations

import os
import sys

from bbsengine6.auth.cli import _log_outcome, _make_logger, _read_checkpassword_stdin
from bbsengine6.auth.verify import verify_member


_LOG = _make_logger("bbsengine6.auth.dovecot")


def _userdb_lines() -> list[str]:
    """Build the userdb-style lines Dovecot expects on stdout."""
    home = os.environ.get("BBSENGINE6_AUTH_MAIL_HOME", "/var/vmail/%d/%n")
    mail = os.environ.get(
        "BBSENGINE6_AUTH_MAIL_LOCATION", "maildir:~/Maildir"
    )
    uid = os.environ.get("BBSENGINE6_AUTH_VMAIL_UID", "vmail")
    gid = os.environ.get("BBSENGINE6_AUTH_VMAIL_GID", "vmail")
    return [
        f"home={home}",
        f"mail={mail}",
        f"uid={uid}",
        f"gid={gid}",
        f"userdb_home={home}",
        f"userdb_mail={mail}",
        f"userdb_uid={uid}",
        f"userdb_gid={gid}",
    ]


def main(argv: list[str] | None = None) -> int:
    user = os.environ.get("AUTH_USER", "").strip()
    if not user:
        _log_outcome(_LOG, user="", outcome="missing-auth-user")
        return 1
    password = _read_checkpassword_stdin()
    if password is None:
        _log_outcome(_LOG, user=user, outcome="missing-password")
        return 1
    try:
        ok, outcome = verify_member(user, password)
    except Exception as exc:
        _LOG.error("db-error user=%s err=%s", user, exc.__class__.__name__)
        return 2
    _log_outcome(_LOG, user=user, outcome=outcome)
    if not ok:
        return 1
    out = sys.stdout
    for line in _userdb_lines():
        out.write(line + "\n")
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
