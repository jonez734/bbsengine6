"""
Verify database superuser permissions and role existence.

Checks that the current user (based on login ID) exists as a database role
with appropriate superuser permissions for BBS engine initialization.

SECURITY: the previous version accepted any role that combined CREATEDB +
CANLOGIN + CREATEROLE as superuser-equivalent. That is over-broad: a
non-superuser role with those three flags can create databases, create
roles, and log in, but cannot run SECURITY DEFINER functions as the
owner. Granting such a role "superuser" status for bootstrap purposes
lets it escalate by creating additional roles and grants. The check now
requires `rolsuper` only.
"""

from bbsengine6 import io, database, util

from bbsengine6.backend import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return lib.issysop(args, **kwargs)


def main(args, **kwargs):
    conn = kwargs.get("conn", None)
    pool = kwargs.get("pool", None)
    currentloginid = util.getcurrentloginid(args)
    if database.rolexists(args, currentloginid, conn=conn, mogrify=True) is False:
        io.echo(
            f"{{var:labelcolor}}role '{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' does not exist"
        )
        return False
    privs = database.get_role_privs(args, currentloginid, conn=conn, pool=pool)
    io.echo(f"{privs=}", level="debug")
    if not privs:
        io.echo(
            f"'{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' does not have correct privs "
            f"(or lookup failed)"
        )
        return False
    if privs.get("rolsuper") is True:
        io.echo(
            f"'{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' has correct privs (superuser)"
        )
        return True
    io.echo(
        f"'{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' is not a superuser; "
        f"the BBS engine bootstrap requires rolsuper. "
        f"Run 'ALTER ROLE {currentloginid} WITH SUPERUSER;' and retry.",
        level="error",
    )
    return False
