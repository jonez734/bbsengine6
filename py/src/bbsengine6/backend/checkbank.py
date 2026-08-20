from bbsengine6 import io, database

from bbsengine6.backend import lib


TARGET_ROLE = "zoid6"


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def _ensure_zoid6_owner(args, conn):
    """Reassign the ``bank`` schema to ``zoid6`` if it currently has a
    different owner (typically the bootstrap principal).

    Mirrors the engine schema block in ``checkengine`` and the casino
    schema block in ``casino.startup.checkcasino``. The bank schema is
    BBS-owned and should have ``zoid6`` as its canonical owner so the
    SECURITY DEFINER helpers in ``public`` (also owned by ``zoid6``)
    can ``GRANT`` on it under NOSUPERUSER if a future feature routes
    bank grants through ``manage_schema_priv`` instead of issuing
    them directly from the bootstrap superuser.

    Idempotent. ``TARGET_ROLE`` is a module constant.
    """
    io.echo(
        f"{{var:labelcolor}}  bank schema ownership → "
        f"{{var:valuecolor}}{TARGET_ROLE}{{var:labelcolor}}: ",
        end="",
    )
    try:
        with database.cursor(conn=conn) as cur:
            cur.execute(
                "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
                "FROM pg_namespace WHERE nspname = 'bank'"
            )
            row = cur.fetchone()
            if row is None:
                io.echo("skip (bank schema not present)")
                return
            current_owner = row["owner"] if isinstance(row, dict) else row[0]
            if current_owner == TARGET_ROLE:
                io.echo(f"{{level.ok}}already {TARGET_ROLE} {{/all}}")
                return
            cur.execute(
                f"ALTER SCHEMA bank OWNER TO {TARGET_ROLE}"
            )
        io.echo(
            f"{{level.ok}}reassigned{{/all}} "
            f"(was '{current_owner}', now '{TARGET_ROLE}')"
        )
    except Exception as e:
        io.echo(
            f"{{var:level.error}}fail {{/all}}", level="error"
        )
        io.echo(f"  {e}", level="error")
        raise


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

    if failcount == 0:
        _ensure_zoid6_owner(args, conn)

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
