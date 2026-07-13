"""
Verify and initialize core engine schema classes.

Creates the fundamental engine schema objects in dependency order:
  - engine.__member (table)
  - engine.member (view, depends on engine.__member)
  - engine.__session (table, FK to engine.__member)
  - engine.session (view, depends on engine.__session and engine.__member)
  - engine.__refcode (table, FK to engine.__member)
  - engine.refcode (view, depends on engine.__refcode and engine.__member)
  - engine.map_refcode_use (table, FK to engine.__member and engine.__refcode)
  - engine.__folder (table, FK to engine.__member)
  - engine.folder (view, depends on engine.__folder and engine.__member)
"""

from bbsengine6 import io, database
from bbsengine6.database import classexists

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


classlist = (
    ("engine.__member", "member.sql"),
    ("engine.member", "memberview.sql"),

    ("engine.__session", "session.sql"),
    ("engine.session", "session_view.sql"),

    ("engine.__refcode", "refcode.sql"),
    ("engine.refcode", "refcode.sql"),
    ("engine.map_refcode_use", "refcode.sql"),

    ("engine.__folder", "folder.sql"),
    ("engine.folder", "folderview.sql"),
)


def main(args, **kwargs) -> bool:
    def _work(conn):
        lib._ensure_autocommit_off(conn)
        failcount = 0

        for cls, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{cls}{{var:labelcolor}}: ",
                end="",
            )
            if classexists(args, cls, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(cls)
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
                        f"checkclasses: retry exhausted for {cls}: {e}"
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
