"""
Verify and initialize engine message tables.

Installs the unified pub/sub message system (Phase 1B: core message
tables, Phase 1C: groups, blocking, rate limiting) into the engine
schema.

Dependencies:
  - engine schema (checkengine)
  - engine.__member (checkclasses)
  - engine.notify_urgency_enum (installed here idempotently from notify.sql)
"""

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
    ("engine.__message", "message.sql"),
    ("engine.__message_recipient", "message.sql"),
    ("engine.__message_group", "message_groups.sql"),
    ("engine.__message_group_member", "message_groups.sql"),
    ("engine.__message_block", "message_groups.sql"),
    ("engine.__message_type", "message_groups.sql"),
    ("engine.__message_rate_limit", "message_groups.sql"),
)


def main(args, **kwargs) -> bool:
    def _work(conn):
        lib._ensure_autocommit_off(conn)
        failcount = 0

        # --- urgency enum (Phase 1B dependency) ---
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
                        f"checkmessage: retry exhausted for enum {c}: {e}"
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

        # --- message tables (Phase 1B + 1C) ---
        for c, sql in classlist:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{c}{{var:labelcolor}}: ",
                end="",
            )
            if classexists(args, c, conn=conn) is False:
                io.echo("import ", end="")
                sp = lib._sanitize_sp(c)
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
                        f"checkmessage: retry exhausted for {c}: {e}"
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
