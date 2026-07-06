"""
Verify and create the main BBS database.

Checks if the main database exists and creates it if necessary,
then grants CONNECT to the standard roles (term, web, sysop, member).
"""

from bbsengine6 import io, database

from bbsengine6.backend import lib


ROLES = ("term", "web", "sysop", "member")


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo(
            "bbsengine6.backend.checkdatabase.100: "
            "could not connect to 'postgres'",
            level="error",
        )
        return False

    with pool:
        try:
            if database.exists(args, args.databasename, pool=pool) is True:
                io.echo(
                    f"{{var:labelcolor}}database "
                    f"{{var:valuecolor}}{args.databasename}{{var:labelcolor}}: "
                    f" ok ",
                    level="ok",
                )
                return True

            io.echo(
                f"{{var:labelcolor}}database "
                f"{{var:valuecolor}}{args.databasename}{{var:labelcolor}}: "
                f"create ",
                end="",
            )
            with database.connect(args, pool=pool) as conn:
                conn.autocommit = True
                if database.create(args, args.databasename, conn=conn) is False:
                    return False
        except Exception as e:
            io.echo_traceback(f"bbsengine6.backend.checkdatabase.120: {e}")
            return False

        lib.ok()

        for role in ROLES:
            io.echo(
                f"{{var:labelcolor}}grant {{var:valuecolor}}connect{{var:labelcolor}} "
                f"on {{var:valuecolor}}{args.databasename}{{var:labelcolor}} to "
                f"{{var:valuecolor}}{role}{{var:labelcolor}}: ",
                end="",
            )
            if (
                database.manage_database_priv(
                    args, "grant", "connect", args.databasename, role, pool=pool, **kwargs
                )
                is False
            ):
                lib.fail()
                return False
            lib.ok()

    return True
