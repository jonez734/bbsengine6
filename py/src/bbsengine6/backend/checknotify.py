"""
Verify and initialize notification system schema.

Checks that all notification-related types and classes exist in the database,
including notification tables, recipient mapping, and notification views.
"""

from bbsengine6 import io, database
from bbsengine6.database import classexists, typeexists

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return True


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
        failcount = 0

        for c, sql in enumlist:
            io.echo(
                f"{{var:labelcolor}}type {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if typeexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                if database.importsql(args, sql, conn=conn) is False:
                    io.echo(" fail ", level="error")
                    conn.rollback()
                    failcount += 1
                else:
                    io.echo("ok", level="ok")
                    conn.commit()
            else:
                io.echo("ok", level="ok")

        for c, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if classexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                if database.importsql(args, sql, conn=conn) is False:
                    io.echo(" fail ", level="error")
                    conn.rollback()
                    failcount += 1
                else:
                    io.echo("ok", level="ok")
                    conn.commit()
            else:
                io.echo("ok", level="ok")

        return True if failcount == 0 else False

    conn = kwargs.get("conn", None)
    return _work(conn)
