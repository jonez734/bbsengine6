"""
Reassign ownership of the public.* SECURITY DEFINER helpers to ``zoid6``.

This module exists to migrate databases that were bootstrapped under the
old ownership model — where the SECURITY DEFINER helpers
(``manage_schema_priv``, ``manage_database_priv``, ``manage_role_privs``,
``manage_secondary_role``, ``get_role_privs``) were created and owned by
the bootstrap principal (``args.databaseuser`` / ``getpass.getuser()``,
typically a login superuser) — onto the new dedicated owner role
``zoid6`` (see ``checkzoid6role``).

After ``checkfunctions`` has installed (or re-installed) the helpers,
this module runs once per database and:

1. Looks up each helper's current ``pg_proc.proowner`` via
   ``pg_roles``.
2. If the owner is anything other than ``zoid6``, issues
   ``ALTER FUNCTION public.<name>(<args>) OWNER TO zoid6`` (using
   ``pg_get_function_identity_arguments`` so the signature always
   matches, regardless of how it was originally declared).
3. Prints a verbose per-function audit line so the operator can see
   exactly which functions moved owners on first run.

Idempotent: re-running on a database where the helpers are already
owned by ``zoid6`` is a no-op. The module does not create the role —
``checkzoid6role`` is responsible for that and runs earlier in
``stage_zero``.

Requires a connection (``conn=``) and an open transaction; the
bootstrap loop in ``stage_zero`` opens one and commits at the end.
"""

from bbsengine6 import database, io

from . import lib


TARGET_ROLE = "zoid6"

# Mirrors the loop in ``backend.checkengine``. Keep in lock-step; if
# a helper is added there, add it here so it gets reassigned on
# upgrade.
HELPERS = (
    "manage_schema_priv",
    "manage_database_priv",
    "manage_role_privs",
    "manage_secondary_role",
    "get_role_privs",
)


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def _qualified_owner(args, name, conn):
    """Return (schema, function_name, args, owner) for ``name`` in
    public, or ``None`` if the function does not exist.

    ``args`` is the identity-args string from
    ``pg_get_function_identity_arguments(p.oid)`` and is what
    ``ALTER FUNCTION ... (<args>)`` expects.
    """
    sql = (
        "SELECT pg_catalog.pg_get_function_identity_arguments(p.oid) AS args, "
        "       r.rolname AS owner "
        "FROM pg_proc p "
        "JOIN pg_namespace n ON p.pronamespace = n.oid "
        "JOIN pg_roles r ON p.proowner = r.oid "
        "WHERE p.proname = %s AND n.nspname = 'public'"
    )
    with database.cursor(conn=conn) as cur:
        cur.execute(sql, (name,))
        row = cur.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return ("public", name, row["args"], row["owner"])
    return ("public", name, row[0], row[1])


def main(args, **kwargs):
    failcount = 0
    conn = kwargs.get("conn", None)

    io.echo(
        f"{{var:labelcolor}}helper ownership → {{var:valuecolor}}{TARGET_ROLE}"
        f"{{var:labelcolor}}:",
    )

    for fn in HELPERS:
        io.echo(
            f"  {{var:labelcolor}}public.{fn}{{var:labelcolor}}: ",
            end="",
        )
        info = _qualified_owner(args, fn, conn)
        if info is None:
            io.echo(
                "skip (not installed; checkfunctions will install on next run)",
            )
            continue
        _schema, _name, fn_args, current_owner = info
        if current_owner == TARGET_ROLE:
            io.echo(f"{{level.ok}}already {TARGET_ROLE} {{/all}}")
            continue

        # Reassign. We pass the conn through; the caller's transaction
        # owns commit/rollback. The ALTER FUNCTION statement is
        # constructed from the schema-qualified function name and the
        # identity-args string returned by
        # pg_get_function_identity_arguments, so the signature always
        # matches regardless of how the function was originally
        # declared. TARGET_ROLE is a module constant, never user
        # input.
        with database.cursor(conn=conn) as cur:
            try:
                cur.execute(
                    f"ALTER FUNCTION public.{fn}({fn_args}) "
                    f"OWNER TO {TARGET_ROLE}"
                )
            except Exception as e:
                io.echo(
                    f"{{var:level.error}}fail {{/all}}", level="error"
                )
                io.echo(f"  {e}", level="error")
                failcount += 1
                continue

        io.echo(
            f"{{level.ok}}reassigned{{/all}} "
            f"(was '{current_owner}', now '{TARGET_ROLE}')"
        )

    lib.hr(failcount)
    return True if failcount == 0 else False
