"""
Check and initialize database roles for BBS engine.

Verifies that all required PostgreSQL roles exist (web, sysop, term, member)
and creates them if necessary with appropriate permissions for system operation.
"""

from bbsengine6 import database, io

from . import lib

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    failcount = 0
    conn = kwargs.get("conn", None)
    roles = ("member", "web", "sysop", "term")
    for r in roles:
        io.echo(
            f"{{var:labelcolor}}role {{var:valuecolor}}{r!s}{{var:labelcolor}}: ",
            end="",
        )
        if database.rolexists(args, r, conn=conn) is False:
            io.echo("create ", end="")
            if (
                database.createrol(
                    args,
                    r,
                    conn=conn,
                    superuser=False,
                    login=False,
                    createdb=False,
                    createrole=False,
                )
                is False
            ):
                io.echo("{{level.error}} fail ", level="error")
                failcount += 1
                break
            else:
                io.echo(f"{{level.ok}}  ok  ")
        else:
            io.echo(f"{{level.ok}}  ok  ", level="ok")

    lib.hr(failcount)
    return True if failcount == 0 else False
