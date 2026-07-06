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
    pool = kwargs.get("pool", None)

    # --- manage_schema_priv helper ---
    # This is a SECURITY DEFINER function in `public` used below to
    # grant schema privileges. checkengine is the first module in
    # both stage 0 (admin DB) and stage 1 (target DB) that needs
    # it, so install it here idempotently if it isn't already
    # present. checkfunctions() also installs it in stage 0 against
    # the admin DB, but stage 1's checkfunctions() only installs
    # engine.* functions and would leave the target DB without the
    # helper.
    if database.functionexists(
        args, "public.manage_schema_priv", conn=conn
    ) is False:
        if database.importsql(
            args, "manage_schema_priv.sql", conn=conn, pool=pool
        ) is False:
            io.echo(
                f"{{var:labelcolor}}function "
                f"{{var:valuecolor}}public.manage_schema_priv"
                f"{{var:labelcolor}}: "
                f"{{level.error}}fail{{/all}}"
            )
            return False

    # --- engine schema ---
    io.echo(
        f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ",
        end="",
    )

    if database.schemaexists(args, "engine", pool=pool, conn=conn) is False:
        io.echo(f"create ", end="")
        if database.createschema(args, "engine", pool=pool, conn=conn) is False:
            lib.fail()
            return False
        lib.ok()
    else:
        lib.ok()

    # --- schema privs ---
    for role in ("web", "term", "sysop", "member"):
        if (database.manage_schema_priv(
            args, "grant", "usage", "engine", role, conn=conn, pool=pool
        ) is False):
            break

    database.manage_schema_priv(
        args, "grant", "create", "engine", "sysop", conn=conn, pool=pool
    )

    # --- classes in dependency order ---
    classes = (
        ("engine.__member", "member.sql"),
        ("engine.member", "member.sql"),
        ("engine.member_flag", "member_flag.sql"),
        ("engine.map_member_flag", "map_member_flag.sql"),

        ("engine.__session", "session.sql"),
        ("engine.session", "session_view.sql"),

#        ("engine.__notify", "notify.sql"),
#        ("engine.__notify_recipient", "notify_recipient.sql"),
#        ("engine.__notify_block", "notify_block.sql"),
#        ("engine.__notify_group", "notify_group.sql"),
#        ("engine.__notify_type", "notify_type.sql"),
#        ("engine.__notify_rate_limit", "notify_rate_limit.sql"),

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
                database.importsql(args, sql, conn=conn, pool=pool)
                is False
            ):
                lib.fail()
                failcount += 1
                break
            else:
                lib.ok()
        else:
            lib.ok()

    lib.hr(failcount)

    return True if failcount == 0 else False
