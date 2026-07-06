"""
Verify and initialize database functions (stored procedures).

Creates and validates all required PostgreSQL stored procedures and functions
that implement the business logic for the BBS engine.
"""

from bbsengine6 import io, database, util

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return True


def main(args, **kwargs):
    io.echo(f"bbsengine6.backend.checkfunctions.100: {kwargs=}", level="debug")

    stage = kwargs.pop("stage", 0)
    conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)


    def _work(conn):
        failcount = 0
        if stage == 0: # postgres
            funcs = (
                "public.get_role_privs",
                "public.manage_secondary_role",
                "public.manage_role_privs",
                "public.manage_database_priv",
                "public.manage_schema_priv",
            )
        else: # zoid6
            funcs = (
                "engine.getflags",
                "engine.checkmemberflag",
            )

        for f in funcs:
            io.echo(
                f"{{var:labelcolor}}function {{var:valuecolor}}{f}{{var:labelcolor}}: {{var:valuecolor}}",
                end="",
            )
            if database.functionexists(args, f, conn=conn) is False:
                io.echo("import ", end="")
                f = f.replace("engine.", "")
                f = f.replace("public.", "")
                if not f.endswith(".sql"):
                    f += ".sql"
                if database.importsql(args, f, pool=pool, conn=conn) is False:
                    lib.fail()
                    failcount += 1
                    break
                else:
                    lib.ok()
            else:
                lib.ok()
        lib.hr(failcount)
        return True if failcount == 0 else False

    return _work(conn)
