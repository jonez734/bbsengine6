"""
Check and initialize database roles for BBS engine.

Verifies that all required PostgreSQL roles exist (web, sysop, term)
and creates them if necessary with appropriate permissions for system operation.
"""

from bbsengine6 import database, io


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    roles = ("web", "sysop", "term")  # , "www-data")
    io.echo(f"con.checkroles.100: {kwargs=}", level="debug")
    for r in roles:
        io.echo(
            f"{{var:labelcolor}}role {{var:valuecolor}}{r!s}{{var:labelcolor}}: ",
            end="",
        )
        if database.rolexists(args, r, **kwargs) is False:
            io.echo("create ", end="")
            if (
                database.createrol(args, r, superuser=False, login=False, **kwargs)
                is False
            ):
                io.echo("fail", level="error")
                return False
            else:
                io.echo("ok", level="ok")
        else:
            io.echo("ok", level="ok")

    return True
