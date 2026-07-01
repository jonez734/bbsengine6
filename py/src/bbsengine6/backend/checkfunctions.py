"""
Verify and initialize database functions (stored procedures).

Creates and validates all required PostgreSQL stored procedures and functions
that implement the business logic for the BBS engine.
"""

from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return True


def main(args, **kwargs):
    stage = kwargs.pop("stage", 0)
    conn = kwargs.get("conn", None)

    failcount = 0

    def _work(conn):
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
                "engine.checkflag",
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
                if database.importsql(args, f, **kwargs) is False:
                    io.echo(f"{{level.error}} fail ")
                    conn.rollback()
                else:
                    io.echo(f"{{level.ok}}  ok  ")
                    conn.commit()
            else:
                io.echo(f"{{level.ok}}exists")
        if failcount == 0:
            util.hr()
        else:
            util.hr(color="{level.error}")
        return True if failcount == 0 else False

    return _work(conn)
