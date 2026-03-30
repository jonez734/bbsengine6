"""
Verify and create the main BBS database.

Checks if the main database exists and creates it if necessary,
initializing all required settings and permissions.
"""

import psycopg
from bbsengine6 import io, database

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


# def database_exists(connection, dbname):
#    query = "SELECT 1 FROM pg_database WHERE datname = %s"
#    with connection.cursor() as cur:
#        cur.execute(query, (dbname,))
#        return False if cur.rowcount == 0 else True


def main(args, **kwargs):
    pool = kwargs.get("pool", None)
    if pool is None:
        io.echo("database pool not available", level="error")
        return False
    with database.connect(args, pool=pool) as conn:
        try:
            io.echo(
                f"{{var:labelcolor}}database {{var:valuecolor}}{args.databasename}{{var:labelcolor}}: ",
                end="",
            )
            if database.exists(args, args.databasename, pool=pool) is True:
                io.echo(" ok ", level="ok")
                return True
        except psycopg.Error as e:
            io.echo(f"An error occurred: {e}", level="error")
            raise

    io.echo("create ", end="")
    with database.connect(args, pool=pool) as conn:
        conn.autocommit = True
        if database.create(args, args.databasename, conn=conn) is False:
            io.echo("fail", level="error")
            conn.rollback()
            return False
        else:
            io.echo(" ok ", level="ok")
            conn.commit()
            return True

    for r in ("term", "web", "sysop"):
        io.echo(
            f"{{var:labelcolor}}grant {{var:valuecolor}}connect{{var:labelcolor}} on {{var:valuecolor}}{args.databasename}{{var:labelcolor}} to {{var:valuecolor}}{r}{{var:labelcolor}}: ",
            end="",
        )
        if (
            database.manage_database_priv(
                args, "grant", "connect", args.databasename, r, **kwargs
            )
            is False
        ):
            io.echo("fail", level="error")
            return False
        io.echo(" ok ", level="ok")

    return True
