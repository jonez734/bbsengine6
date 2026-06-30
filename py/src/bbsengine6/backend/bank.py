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

    # --- bank schema ---
    io.echo(
        f"{{var:labelcolor}}schema {{var:valuecolor}}bank{{var:labelcolor}}: ",
        end="",
    )
    if database.schemaexists(args, "bank", conn=conn) is False:
        if database.createschema(args, "bank", conn=conn) is False:
            io.echo(f"{{level.error}} fail ")
            return False
    io.echo(" ok ", level="ok")

    # --- bank schema privs ---
    io.echo(f"bank schema privs: ", end="", flush=True)
    for role in ("web", "term", "sysop", "member"):
        if database.manage_schema_priv(
            args, "grant", "usage", "bank", role, conn=conn
        ) is False:
            io.echo(f"{{level.error}} fail ")
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

    failcount = 0
    for cls, sql in bank_classes:
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
