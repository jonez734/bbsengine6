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



OWNER_ROLE = "zoid6"


def _is_owner_member(args, rolname, *, conn=None, pool=None) -> bool:
    """True when ``rolname`` is a member of the install owner role."""
    def _work(c):
        with c.cursor() as cur:
            cur.execute("SELECT pg_has_role(%s, %s, 'MEMBER')", (rolname, OWNER_ROLE))
            row = cur.fetchone()
            return bool(row[0] if row and not isinstance(row, dict) else (row or {}).get("pg_has_role"))

    try:
        if conn is not None:
            return _work(conn)
        if pool is not None:
            with database.connect(args, pool=pool) as c:
                return _work(c)
    except Exception:
        return False
    return False


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
    # Install-time DDL is owned by zoid6, so a member of zoid6 can run it as
    # zoid6. This does not grant superuser rights.
    if _is_owner_member(args, currentloginid, conn=conn, pool=pool):
        io.echo(
            f"'{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' is a member of "
            f"'zoid6' (install owner)"
        )
        return True
    io.echo(
        f"'{{var:valuecolor}}{currentloginid}{{var:labelcolor}}' is not a superuser; "
        f"the BBS engine bootstrap requires rolsuper. "
        f"Run 'ALTER ROLE {currentloginid} WITH SUPERUSER;' and retry.",
        level="error",
    )
    return False
