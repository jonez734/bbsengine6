from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    conn = kwargs.get("conn", None)

    # --- engine schema ---
    io.echo(
        f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ",
        end="",
    )

    if database.schemaexists(args, "engine", conn=conn) is False:
        io.echo(f"create ", end="")
        if database.createschema(args, "engine", conn=conn) is False:
            io.echo("fail", level="error")
            return False
        io.echo(" ok ", level="ok")
    else:
        io.echo("exists")

    # --- schema privs ---
    for role in ("web", "term", "sysop", "member"):
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
        ("engine.pgrole", "pgrole.sql"),
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
                database.importsql(args, sql, conn=conn)
                is False
            ):
                io.echo("fail", level="error")
                failcount += 1
            else:
                io.echo(" ok ", level="ok")
        else:
            io.echo("ok", level="ok")

    return True if failcount == 0 else False
