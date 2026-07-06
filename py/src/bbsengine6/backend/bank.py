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

    failcount = 0
    # --- bank schema ---
    io.echo(
        f"{{var:labelcolor}}schema {{var:valuecolor}}bank{{var:labelcolor}}: ",
        end="",
    )
    if database.schemaexists(args, "bank", conn=conn, pool=pool) is False:
        if database.createschema(args, "bank", conn=conn, pool=pool) is False:
            failcount += 1
            lib.fail()
    else:
        lib.ok()

    if failcount > 0:
        lib.hr(failcount)
        return False

    # --- bank schema privs ---
    io.echo(f"{{labelcolor}}bank schema privs: {{/all}}", flush=True)
    for role in ("web", "term", "sysop", "member"):
        io.echo(f"{{labelcolor}}role {{valuecolor}}{role}{{labelcolor}}: ", end="")
        if database.manage_schema_priv(
            args, "grant", "usage", "bank", role, conn=conn, pool=pool
        ) is False:
            failcount += 1
            lib.fail()
            break
        else:
            lib.ok()

    io.echo(f"{{labelcolor}}grant role '{{valuecolor}}sysop' create {{labelcolor}}on schema bank: ", end="", flush=True)
    if (database.manage_schema_priv(
        args, "grant", "create", "bank", "sysop", conn=conn, pool=pool
    )) is False:
        failcount += 1
        lib.fail()
    else:
        lib.ok()

    lib.hr(failcount)
    if failcount > 0:
        return False

    # --- bank classes ---
    bank_classes = (
        ("bank.__account", "bank.sql"),
        ("bank.account", "bank.sql"),
        ("bank.__transaction", "bank.sql"),
        ("bank.transaction", "bank.sql"),
        ("bank.__transfer", "bank.sql"),
        ("bank.transfer", "bank.sql"),
    )

    failcount = 0
    for cls, sql in bank_classes:
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
                failcount += 1
                break
            else:
                lib.ok()
        else:
            lib.ok()

    lib.hr(failcount)

    return True if failcount == 0 else False
