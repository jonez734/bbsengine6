from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)

    failcount = 0
    io.echo("schema bank: ", end="")
    if database.schemaexists(args, "bank", conn=conn, pool=pool) is False:
        io.echo("import ", end="")
        if database.importsql(args, "bank_schema.sql", conn=conn, pool=pool) is False:
            failcount += 1
            lib.fail()
        else:
            lib.ok()
    else:
        lib.ok()

    lib.hr(failcount)
    if failcount > 0:
        return False

    bank_classes = (
        ("bank.__account", "bank_account.sql"),
        ("bank.account", "bank_account_view.sql"),
        ("bank.__transaction", "bank_transaction.sql"),
        ("bank.transaction", "bank_transaction_view.sql"),
        ("bank.__transfer", "bank_transfer.sql"),
        ("bank.transfer", "bank_transfer_view.sql"),
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
