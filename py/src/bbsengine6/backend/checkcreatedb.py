"""
Verify the connecting role has CREATEDB privilege.

This must run before checkdatabase, because checkdatabase may need to
CREATE the target database (e.g. on a fresh install where the 'zoid6'
database does not yet exist). If the role lacks CREATEDB, the
CREATE DATABASE call will fail with InsufficientPrivilege. We probe
pg_roles.rolcreatedb up front and abort with a clear two-line message
when the privilege is missing.
"""

from bbsengine6 import database, io


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("checkcreatedb: database pool not available", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT rolcreatedb, rolname "
                "FROM pg_roles WHERE rolname = current_user"
            )
            row = cur.fetchone()

    if row is None:
        io.echo(
            "checkcreatedb: could not resolve current_user in pg_roles",
            level="error",
        )
        return False

    rolcreatedb, rolname = row
    if not rolcreatedb:
        io.echo(
            f"current user '{rolname}' lacks CREATEDB privilege; "
            f"cannot create database '{args.databasename}'",
            level="error",
        )
        io.echo(
            f"startup aborted; grant CREATEDB to '{rolname}' and re-run",
            level="error",
        )
        return False

    io.echo(
        f"checkcreatedb: user '{rolname}' has CREATEDB", level="ok"
    )
    return True
