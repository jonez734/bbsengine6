"""
checkmember_moniker_format - always-run migration for the moniker
constraint.

The checkclasses module loads ``member.sql`` only when ``engine.__member``
does not exist, so the inline DO migration in that file never fires on
a pre-existing DB. This module re-runs the same migration idempotently
on every startup so legacy installs pick up the namespaced-moniker
pattern as soon as they're upgraded.

The migration is a no-op when the constraint already permits namespaced
monikers (fresh DBs, DBs that have already been migrated).
"""

from bbsengine6 import database, io
from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def main(args, **kwargs) -> bool:
    def _work(conn):
        lib._ensure_autocommit_off(conn)
        ok = database.importsql(
            args, "checkmember_moniker_format.sql",
            conn=conn, rollback=False,
        )
        if ok is False:
            io.echo(
                "checkmember_moniker_format: importsql returned false",
                level="error",
            )
            return False
        io.echo("checkmember_moniker_format: ok", level="ok")
        return True

    conn = kwargs.get("conn", None)
    return _work(conn)
