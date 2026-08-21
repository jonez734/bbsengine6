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

    # --- manage_schema_priv helper ---
    # This is a SECURITY DEFINER function in `public` used below to
    # grant schema privileges. checkengine is the first module in
    # both stage 0 (admin DB) and stage 1 (target DB) that needs
    # it, so install it idempotently if it isn't already
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

    # SECURITY: verify the owner of every SECURITY DEFINER helper
    # before calling it. If the function has been replaced or its
    # owner changed, calls below would execute as the new owner and
    # could escalate privileges. The acceptable owner is the
    # dedicated, unprivileged role ``zoid6`` (created by
    # ``checkzoid6role`` and owned by ``checkzoid6owner``); ``postgres``
    # is also accepted for one release so databases bootstrapped
    # under the previous model (where the SQL files used
    # ``SET ROLE postgres`` to make ``postgres`` the immediate creator)
    # pass the gate on first run. ``postgres`` will be removed from
    # this list in a subsequent release — see
    # ``bbsengine6/TODO_zoid6_role.md``.
    acceptable_owners = ("zoid6", "postgres")
    for secdef_fn in (
        "public.manage_schema_priv",
        "public.manage_database_priv",
        "public.manage_role_privs",
        "public.manage_secondary_role",
        "public.get_role_privs",
    ):
        if not database.functionexists(args, secdef_fn, conn=conn):
            continue  # Not yet installed; skip the owner check.
        if not database.verify_function_owner(
            args, secdef_fn, acceptable_owners, conn=conn
        ):
            io.echo(
                f"checkengine: refusing to use {secdef_fn} (owner mismatch); "
                f"see error above",
                level="error",
            )
            return False

    # --- engine schema ---
    # The schema must be owned by ``zoid6`` so that the SECURITY
    # DEFINER helper ``manage_schema_priv`` (also owned by ``zoid6``)
    # can issue GRANT statements on it. ``zoid6`` is NOSUPERUSER and
    # can only GRANT on objects it owns. Without this, every grant in
    # the loop below would fail with
    # ``permission denied for schema engine`` once the helpers are
    # owned by ``zoid6``.
    io.echo(
        f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}}: ",
        end="",
    )

    if database.schemaexists(args, "engine", pool=pool, conn=conn) is False:
        io.echo(f"create ", end="")
        # ``createschema`` does not accept an owner kwarg, so issue
        # the DDL directly so the new schema is owned by ``zoid6``
        # from the start (``CREATE SCHEMA ... AUTHORIZATION zoid6``).
        try:
            with database.cursor(conn=conn) as cur:
                cur.execute("CREATE SCHEMA engine AUTHORIZATION zoid6")
        except Exception as e:
            io.echo(f"{{var:level.error}}fail {{/all}}", level="error")
            io.echo(f"  {e}", level="error")
            return False
        lib.ok()
    else:
        # BC: an existing engine schema may be owned by the previous
        # bootstrap principal (e.g. jam, opencode). Reassign to
        # zoid6 so the SECDEF helper grants below can succeed.
        try:
            with database.cursor(conn=conn) as cur:
                cur.execute(
                    "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
                    "FROM pg_namespace WHERE nspname = 'engine'"
                )
                row = cur.fetchone()
                # ``database.cursor`` returns dict rows by default;
                # handle either shape defensively.
                if row is None:
                    current_owner = None
                elif isinstance(row, dict):
                    current_owner = row.get("owner")
                else:
                    current_owner = row[0]
                if current_owner and current_owner != "zoid6":
                    cur.execute("ALTER SCHEMA engine OWNER TO zoid6")
                    io.echo(
                        f"{{level.ok}}ok{{/all}} (reassigned from "
                        f"'{current_owner}' to 'zoid6')"
                    )
                else:
                    lib.ok()
        except Exception as e:
            io.echo(f"{{var:level.error}}fail {{/all}}", level="error")
            io.echo(f"  {e}", level="error")
            return False

    # --- schema privs ---
    for role in ("web", "term", "sysop", "member"):
        if (database.manage_schema_priv(
            args, "grant", "usage", "engine", role, conn=conn, pool=pool
        ) is False):
            break

    database.manage_schema_priv(
        args, "grant", "create", "engine", "sysop", conn=conn, pool=pool
    )

    return True
