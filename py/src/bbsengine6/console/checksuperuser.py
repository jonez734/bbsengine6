"""
Verify database superuser permissions and role existence.

Checks that the current user (based on login ID) exists as a database role
with appropriate superuser permissions for BBS engine initialization.
"""

from bbsengine6 import io, database, util

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    util.heading("checking for database superuser")
    currentloginid = util.getcurrentloginid(args)
    if database.rolexists(args, currentloginid, mogrify=True, **kwargs) is False:
        io.echo(
            f"{{var:labelcolor}}role {{var:valuecolor}}{currentloginid}{{var:labelcolor}} does not exist"
        )
        return False
    privs = database.get_role_privs(args, currentloginid, **kwargs)
    io.echo(f"{privs=}", level="debug")
    if privs == {}:
        io.echo(
            f"{{var:valuecolor}}{currentloginid}{{var:labelcolor}} does not have privs"
        )
        return False
    if privs["rolsuper"] is True:
        io.echo(
            f"{{var:valuecolor}}{currentloginid}{{var:labelcolor}} has correct privs (superuser)"
        )
        return True
    else:
        if (
            privs["rolcreatedb"] is True
            and privs["rolcanlogin"] is True
            and privs["rolcreaterole"] is True
        ):
            io.echo(
                f"{{var:valuecolor}}{currentloginid}{{var:labelcolor}} has correct privs (createdb, canlogin, createrole)"
            )
            return True
    return False
