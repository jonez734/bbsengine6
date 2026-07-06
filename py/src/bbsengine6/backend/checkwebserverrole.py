"""
Verify web server database role exists.

Checks that the www-data database role exists (used by PHP/web interface)
and creates it if necessary with appropriate permissions.
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
    pool = kwargs.get("pool", None)
    io.echo(
        f"{{var:labelcolor}}role {{var:valuecolor}}www-data{{var:valuecolor}}: ", end=""
    )
    if database.rolexists(args, "www-data", conn=conn) is False:
        io.echo(f"{{var:labelcolor}}create ", end="")
        if database.createrol(args, "www-data", conn=conn, login=True) is False:
            io.echo(f"{{var:level.error}}  fail  {{/all}}")
            failcount += 1
        else:
            io.echo(f"{{level.ok}}  ok  {{/all}}")
    else:
        io.echo(f"{{level.ok}}  ok  {{/all}}")

    io.echo(
        f"{{var:labelcolor}}granting {{var:valuecolor}}login{{var:labelcolor}} to role {{var:valuecolor}}www-data{{var:labelcolor}}: ",
        end="",
    )
    if (
        database.manage_role_privs(
            args, "www-data", "grant", "login", conn=conn, pool=pool
        )
        is False
    ):
        failcount += 1
        io.echo(f"{{level.error}} fail ")
    else:
        io.echo(f"{{level.ok}}  ok  {{/all}}")

    lib.hr(failcount)
    return True if failcount == 0 else False
