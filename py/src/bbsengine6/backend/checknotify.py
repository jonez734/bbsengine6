"""
Verify and initialize notification system schema.

DEPRECATED: notify schema is being moved to the message_delivery subsystem.
This module will be removed once console has migrated its callers. Until
then the access() and savepoint plumbing is kept current; the SQL imports
remain commented out in checkengine.py.
"""

import warnings

from bbsengine6 import io, database
from bbsengine6.database import classexists, typeexists

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


enumlist = (("engine.notify_urgency_enum", "notify.sql"),)

classlist = (
    ("engine.__notify", "notify.sql"),
    ("engine.__notify_type", "notify_type.sql"),
    ("engine.__notify_recipient", "notify_recipient.sql"),
    ("engine.__notify_block", "notify_block.sql"),
    ("engine.__notify_group", "notify_group.sql"),
    ("engine.__notify_rate_limit", "notify_rate_limit.sql"),
    ("engine.notify", "notifyview.sql"),
    ("engine.notify_unread", "notifyview.sql"),
    ("engine.notify_urgent", "notifyview.sql"),
    ("engine.notify_blocked", "notifyview.sql"),
)


def main(args, **kwargs) -> bool:
    def _work(conn):
        lib._ensure_autocommit_off(conn)
        failcount = 0

        for c, sql in enumlist:
            io.echo(
                f"{{var:labelcolor}}type {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if typeexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(c, prefix="enum_")
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"SAVEPOINT {sp}")
                try:
                    ok = lib.retry_on_transient(
                        lambda: database.importsql(
                            args, sql, conn=conn, rollback=False
                        )
                    )
                except Exception as e:
                    io.echo_traceback(
                        f"checknotify: retry exhausted for enum {c}: {e}"
                    )
                    ok = False
                if ok is False:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                    io.echo(" fail ", level="error")
                    failcount += 1
                else:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"RELEASE SAVEPOINT {sp}")
                    io.echo("ok", level="ok")
            else:
                io.echo("ok", level="ok")

        for c, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if classexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(c, prefix="class_")
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"SAVEPOINT {sp}")
                try:
                    ok = lib.retry_on_transient(
                        lambda: database.importsql(
                            args, sql, conn=conn, rollback=False
                        )
                    )
                except Exception as e:
                    io.echo_traceback(
                        f"checknotify: retry exhausted for class {c}: {e}"
                    )
                    ok = False
                if ok is False:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                    io.echo(" fail ", level="error")
                    failcount += 1
                else:
                    with database.cursor(conn=conn) as cur:
                        cur.execute(f"RELEASE SAVEPOINT {sp}")
                    io.echo("ok", level="ok")
            else:
                io.echo("ok", level="ok")

        if failcount == 0:
            conn.commit()
        else:
            conn.rollback()
        return True if failcount == 0 else False

    conn = kwargs.get("conn", None)
    return _work(conn)


if not getattr(checknotify, "_warned", False):
    warnings.warn(
        "bbsengine6.backend.checknotify is deprecated; "
        "use bbsengine6.message_delivery.* instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    checknotify._warned = True
