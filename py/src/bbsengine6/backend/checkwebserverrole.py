"""
Verify web server database role exists.

Checks that the www-data database role exists (used by PHP/web interface)
and creates it if necessary with appropriate permissions.

SECURITY: the previous version unconditionally granted LOGIN to the
www-data role via a second `manage_role_privs(..., "grant", "login", ...)`
call. That expanded the credential attack surface: even when peer
authentication is configured in pg_hba.conf (the typical deploy), the
role could authenticate with a password. The grant is now applied only
at role-creation time via the `login=True` flag, which is the minimum
needed for the role to function.
"""

from bbsengine6 import database, io

from . import lib

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return lib.issysop(args, **kwargs)


def main(args, **kwargs):
    failcount = 0
    conn = kwargs.get("conn", None)
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

    if failcount == 0:
        io.echo(
            f"{{var:labelcolor}}  grant member to www-data: ", end=""
        )
        try:
            with database.cursor(conn=conn) as cur:
                cur.execute('GRANT member TO "www-data"')
            io.echo(f"{{level.ok}}  ok  {{/all}}")
        except Exception as e:
            io.echo(f"{{var:level.error}}  fail  {{/all}}")
            io.echo(f"  {{var:labelcolor}}{e}", level="error")
            failcount += 1

    lib.hr(failcount)
    return True if failcount == 0 else False
