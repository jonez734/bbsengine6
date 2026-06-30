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

    def _work(conn):
        if stage == 0:
            funcs = (
                "public.get_role_privs",
                "public.manage_secondary_role",
                "public.manage_role_privs",
                "public.manage_database_priv",
                "public.manage_schema_priv",
            )
        else:
            funcs = ("engine.getflags", "engine.checkflag")
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
                    io.echo("fail", level="error")
                    conn.rollback()
                else:
                    io.echo("ok", level="ok")
                    conn.commit()
            else:
                io.echo("exists", level="ok")
        return True

    return _work(conn)
