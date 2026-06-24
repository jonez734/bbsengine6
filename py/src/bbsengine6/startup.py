# startup.py
# Initialises the engine schema, notify tables, and core bbsengine6 structures.

from bbsengine6 import database, io


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return None


def main(args, **kwargs) -> bool:
    def _work(conn):
        io.echo("running bbsengine6 startup...")

        # --- schema ---
        io.echo(
            f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ",
            end="",
        )
        if database.schemaexists(args, "engine", conn=conn) is False:
            if database.createschema(args, "engine", conn=conn) is False:
                io.echo("fail", level="error")
                return False
        io.echo(" ok ", level="ok")

        # --- bank schema ---
        io.echo(
            f"{{var:labelcolor}}schema {{var:valuecolor}}bank{{var:labelcolor}}: ",
            end="",
        )
        if database.schemaexists(args, "bank", conn=conn) is False:
            if database.createschema(args, "bank", conn=conn) is False:
                io.echo("fail", level="error")
                return False
        io.echo(" ok ", level="ok")

        # --- bank schema privs ---
        for role in ("web", "term", "sysop"):
            database.manage_schema_priv(
                args, "grant", "usage", "bank", role, conn=conn
            )
        database.manage_schema_priv(
            args, "grant", "create", "bank", "sysop", conn=conn
        )

        # --- bank classes ---
        bank_classes = (
            ("bank.__account", "bank.sql"),
            ("bank.account", "bank.sql"),
            ("bank.__transaction", "bank.sql"),
            ("bank.transaction", "bank.sql"),
            ("bank.__transfer", "bank.sql"),
            ("bank.transfer", "bank.sql"),
        )

        for cls, sql in bank_classes:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{cls}{{var:labelcolor}}: ",
                end="",
            )
            if database.classexists(args, cls, conn=conn) is False:
                io.echo("import ", end="")
                if (
                    database.importsql(args, sql, conn=conn, package="bbsengine6.sql")
                    is False
                ):
                    io.echo("fail", level="error")
                    failcount += 1
                else:
                    io.echo(" ok ", level="ok")
            else:
                io.echo("ok", level="ok")

        # --- schema privs ---
        for role in ("web", "term", "sysop"):
            database.manage_schema_priv(
                args, "grant", "usage", "engine", role, conn=conn
            )
        database.manage_schema_priv(
            args, "grant", "create", "engine", "sysop", conn=conn
        )

        # --- classes in dependency order ---
        classes = (
            ("engine.__notify", "notify.sql"),
            ("engine.__notify_recipient", "notify_recipient.sql"),
            ("engine.__notify_block", "notify_block.sql"),
            ("engine.__notify_group", "notify_group.sql"),
            ("engine.__notify_type", "notify_type.sql"),
            ("engine.__notify_rate_limit", "notify_rate_limit.sql"),
            ("engine.member_flag", "flag.sql"),
            ("engine.map_member_flag", "map_member_flag.sql"),
            ("engine.__member", "member.sql"),
            ("engine.member", "member.sql"),
            ("engine.__refcode", "refcode.sql"),
            ("engine.refcode", "refcode.sql"),
            ("engine.map_refcode_use", "refcode.sql"),
        )

        failcount = 0
        for cls, sql in classes:
            io.echo(
                f"{{var:labelcolor}}class {{var:valuecolor}}{cls}{{var:labelcolor}}: ",
                end="",
            )
            if database.classexists(args, cls, conn=conn) is False:
                io.echo("import ", end="")
                if (
                    database.importsql(args, sql, conn=conn, package="bbsengine6.sql")
                    is False
                ):
                    io.echo("fail", level="error")
                    failcount += 1
                else:
                    io.echo(" ok ", level="ok")
            else:
                io.echo("ok", level="ok")

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
