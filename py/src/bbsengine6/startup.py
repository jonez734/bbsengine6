# startup.py

from bbsengine6 import database, io

from bbsengine6.backend import lib

def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return None

def main(args, **kwargs) -> bool:
    def _work(conn):
        util.heading("startup")
        if lib.runmodule(args, "stage_zero", **kwargs) is False:
            lib.fail()
            return False
        else:
            lib.ok()

        if stage_one(args, **kwargs) is False:
            lib.fail()
            return False

        # --- 'member' group role ---
        # pgrole.sql creates this, but it isn't processed until later in the
        # class-import phase. Create it here so the schema-priv grants below
        # can reference it on a fresh database.
        io.echo(
            f"{{var:labelcolor}}role {{var:valuecolor}}member{{var:labelcolor}}: ",
            end="",
        )

        for r in ("member", "sysop", "web", "term"):
            io.echo(f"{{labelcolor}}checking role {{valuecolor}}{r}{{labelcolor}}: {{/all}}")
            if database.rolexists(args, r, conn=conn):
                lib.ok()
            else:
                io.echo(f"{{labelcolor}} create: ", end="")
                if database.createrole(args, r, conn=conn, login=False, createdb=False, createrole=False, superuser=False):
                    lib.ok()
                else:
                    lib.fail()

        # --- engine schema ---
        io.echo(
            f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ",
            end="",
        )

        if database.schemaexists(args, "engine", conn=conn) is False:
            io.echo("create ", end="")
            if database.createschema(args, "engine", conn=conn) is False:
                io.echo("fail", level="error")
                return False
        io.echo(" ok ", level="ok")



        # --- classes in dependency order ---
        classes = (
#            ("engine.__notify", "notify.sql"),
#            ("engine.__notify_recipient", "notify_recipient.sql"),
#            ("engine.__notify_block", "notify_block.sql"),
#            ("engine.__notify_group", "notify_group.sql"),
#            ("engine.__notify_type", "notify_type.sql"),
#            ("engine.__notify_rate_limit", "notify_rate_limit.sql"),

            ("engine.member_flag", "flag.sql"),
            ("engine.map_member_flag", "map_member_flag.sql"),
            ("engine.__member", "member.sql"),
            ("engine.member", "member.sql"),

            ("engine.pgrole", "pgrole.sql"),

            ("engine.__refcode", "refcode.sql"),
            ("engine.refcode", "refcode.sql"),
            ("engine.map_refcode_use", "refcode.sql"),
        )

        for cls, sql in classes:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{cls}{{var:labelcolor}}: ",
                end="",
            )
            if database.classexists(args, cls, conn=conn) is False:
                io.echo("import ", end="")
                if (
                    database.importsql(args, sql, conn=conn)
                    is False
                ):
                    lib.fail()
                    failcount += 1
                else:
                    lib.ok()
            else:
                lib.ok()

        if failcount > 0:
            io.echo("bbsengine6 startup failed", level="error")
            conn.rollback()
            return False

        io.echo("bbsengine6 startup complete", level="ok")
        conn.commit()
        return True

    conn = kwargs.get("conn", None)
    io.echo(f"{conn=}", level="debug")
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.startup.100: pool is None", level="error")
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
