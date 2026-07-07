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
    return lib.issysop(args, **kwargs)


classlist = (
    ("engine.__member", "member.sql"),
    ("engine.__session", "session.sql"),
    ("engine.__folder", "folder.sql"),
    ("engine.member", "memberview.sql"),
)


def main(args, **kwargs) -> bool:
    def _work(conn):
        conn.autocommit = False
        failcount = 0
        for c, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if database.classexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(c)
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"SAVEPOINT {sp}")
                # Bounded retry on transient DB errors (lock timeout,
                # deadlock). The savepoint protects the outer
                # transaction; a transient failure rolls back only the
                # savepoint and we re-try the importsql call.
                try:
                    ok = lib.retry_on_transient(
                        lambda: database.importsql(
                            args, sql, conn=conn, rollback=False
                        )
                    )
                except Exception as e:
                    io.echo_traceback(
                        f"checkclasses: retry exhausted for {c}: {e}"
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
