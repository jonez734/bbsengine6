"""
Verify and initialize required database classes (tables/views).

Checks that all necessary table and view definitions exist in the engine schema
and creates them if needed with appropriate structure and permissions.
"""

from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return True


classlist = (
    ("engine.__member", "member.sql"),
    ("engine.__session", "session.sql"),
    ("engine.__folder", "folder.sql"),
    ("engine.member", "memberview.sql"),
)


def main(args, **kwargs) -> bool:
    def _work(conn):
        failcount = 0
        for c, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if database.classexists(args, c, conn=conn) is False:
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
