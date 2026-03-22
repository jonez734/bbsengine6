"""
Verify and create the main BBS database.

Checks if the main database exists and creates it if necessary,
initializing all required settings and permissions.
"""

import psycopg
from bbsengine6 import io, database, util

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
        io.echo(f"bbsengine.con.checkdatabase.100: {pool=}", level="error")
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
            print(f"An error occurred: {e}")
            raise

    # io.echo(f"con.checkdatabase.100: {pool=}", level="debug")
    io.echo("create ", end="")
    with database.connect(args, pool=pool) as conn:
        conn.autocommit = True
        io.echo(f"con.checkdatabase.120: {conn=}", level="debug")
        if database.create(args, args.databasename, conn=conn) is False:
            io.echo("fail", level="error")
            conn.rollback()
            return False
        else:
            io.echo(" ok ", level="ok")
            conn.commit()
            return True

    io.echo("granting connect on {args.databasename}", level="debug")

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

    return "NEEDINFO"

    res = database.exists(args, args.databasename, conn=conn, **kwargs)
    io.echo(f"con.checkdatabase.main.100: {res=}", level="debug")
    if res is False:
        io.echo(
            f"{{var:valuecolor}}{args.databasename}{{var:labelcolor}} does not exist"
        )
        if database.create(args, args.databasename) is False:
            io.echo(
                f"{{var:labelcolor}}database {{var:valuecolor}}{args.databasename}{{var:labelcolor}} could not be created"
            )
            return False
        else:
            io.echo(
                f"{{var:labelcolor}}database {{var:valuecolor}}{args.databasename}{{var:labelcolor}} created"
            )
    if database.schemaexists(args, "engine", **kwargs) is False:
        if database.createschema(args, "engine", **kwargs) is False:
            io.echo(
                f"{{var:labelcolor}}unable to create schema {{var:valuecolor}}engine{{var::labelcolor}}"
            )
            return False
    else:
        io.echo(
            f"{{var:labelcolor}}schema {{var:valuecolor}}engine{{var:labelcolor}} exists"
        )

    if database.classexists(args, "engine.__member", mogrify=True, **kwargs) is False:
        io.echo(f"{{var:valuecolor}}engine.__member{{var:labelcolor}} does not exist")
        return False
    else:
        io.echo(f"{{var:valuecolor}}engine.__member{{var:labelcolor}} exists")

    if database.classexists(args, "engine.member", mogrify=True, **kwargs) is False:
        io.echo(f"{{var:valuecolor}}engine.member{{var:labelcolor}} does not exist")
        return False
    else:
        io.echo(f"{{var:valuecolor}}engine.member{{var:labelcolor}} exists")

    if database.classexists(args, "engine.__session", mogrify=True, **kwargs) is False:
        io.echo(f"{{var:valuecolor}}engine.__session{{var:labelcolor}} does not exist")
        return False
    else:
        io.echo(f"{{var:valuecolor}}engine.__session{{var:labelcolor}} exists")

    if database.classexists(args, "engine.session", mogrify=True, **kwargs) is False:
        io.echo(f"{{var:valuecolor}}engine.session{{var:labelcolor}} does not exist")
        return False
    else:
        io.echo(f"{{var:valuecolor}}engine.session{{var:labelcolor}} exists")

    return True
