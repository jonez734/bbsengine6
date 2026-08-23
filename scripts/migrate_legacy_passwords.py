"""Migrate legacy ``engine.__member.password`` values to fresh bcrypt hashes.

Discovers legacy rows by mirroring the ``chk_member_password_bcrypt``
predicate inverted (anything that would violate the constraint is a
migration candidate: NULL, empty, non-bcrypt prefix, wrong length).
Then re-hashes each row to ``$2b$06$...`` via
``bbsengine6.member.setpassword`` (which delegates to
``bbsengine6.password.hash_password``).

New password for each row follows the ``<moniker><YYYY>*`` template
(``jam2026*``, ``__dealer__2026*``, ...); operators can rotate these
on next login.

Usage::

    python scripts/migrate_legacy_passwords.py
"""

import datetime
import sys

from bbsengine6.console.lib import buildargs
from bbsengine6 import database, io, member, password


args = buildargs().parse_args([])
pool = database.getpool(args)

YEAR = datetime.datetime.now().year

# Mirror ``chk_member_password_bcrypt`` predicate inverted: anything
# that would be rejected by the constraint is a migration candidate.
# Equivalent to ``not bbsengine6.password.is_healthy_hash(password)``
# evaluated row-side by PG.
LEGACY_SQL = (
    "select moniker, password from $engine.__member "
    "where password is null "
    "   or password = '' "
    "   or password !~ '^\\$2[abxy]\\$' "
    "   or length(password) <> 60 "
    "order by moniker"
)


def _migrate_one(cur, moniker: str) -> bool:
    """Re-hash ``moniker`` to bcrypt with template password; return ok."""
    new_password = f"{moniker}{YEAR}*"
    io.echo(f"migrating {moniker} -> bcrypt (new password: {new_password})")
    result = member.setpassword(args, new_password, moniker, cur=cur)
    if result is not True:
        io.echo(f"  setpassword: no row updated for {moniker}", level="error")
        return False
    verify = member.checkpassword(
        args, new_password, membermoniker=moniker, cur=cur
    )
    io.echo(f"  verify: {verify}")
    return verify is True


try:
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            cur.execute(database.query(LEGACY_SQL))
            legacy_rows = cur.fetchall()
            if not legacy_rows:
                io.echo("no legacy password rows; nothing to migrate")
                sys.exit(0)
            io.echo(
                f"found {len(legacy_rows)} legacy row(s) in engine.__member:"
            )
            for row in legacy_rows:
                moniker = row["moniker"]
                stored = row["password"]
                io.echo(
                    f"  {moniker}: classify={password.classify_hash(stored)}"
                )
            failed = []
            for row in legacy_rows:
                if not _migrate_one(cur, row["moniker"]):
                    failed.append(row["moniker"])
            if failed:
                io.echo(
                    f"migration failed for: {', '.join(failed)}",
                    level="error",
                )
                sys.exit(1)
            io.echo(
                "all legacy rows migrated; re-run zoid6 to install "
                "chk_member_password_bcrypt"
            )
finally:
    pool.close()
