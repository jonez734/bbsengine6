"""
Verify the connecting role has CREATEDB privilege.

This must run before checkdatabase, because checkdatabase may need to
CREATE the target database (e.g. on a fresh install where the 'zoid6'
database does not yet exist). If the role lacks CREATEDB, the
CREATE DATABASE call will fail with InsufficientPrivilege. We probe
pg_roles up front and abort with a clear two-line message when the
privilege is missing.

PostgreSQL allows CREATE DATABASE if ANY of the following is true:

  * the role is a superuser (rolsuper)
  * the role has rolcreatedb set
  * the role has been granted CREATE on the target database
    (handled by has_database_privilege, not relevant here when the
    target database does not yet exist)

We check the first two: a superuser can always create a database
even without rolcreatedb, so we must not reject superusers.
"""

from bbsengine6 import database, io


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    # Accept either a pool (preferred, lets us open a short-lived
    # connection) or a caller-supplied conn. Previously this required
    # pool= and printed "pool not available" + returned False if
    # called with only a conn, which was a silent failure: the caller
    # already had a valid conn and the check could have run against
    # it. Caller-supplied conn is used as-is.
    pool = kwargs.get("pool", None)
    conn = kwargs.get("conn", None)
    if pool is None and conn is None:
        io.echo(
            "checkcreatedb: neither pool nor conn supplied; cannot check privs",
            level="error",
        )
        return False

    def _work(c):
        with c.cursor() as cur:
            cur.execute(
                "SELECT rolcreatedb, rolsuper, rolname "
                "FROM pg_roles WHERE rolname = current_user"
            )
            return cur.fetchone()

    if pool is not None:
        with database.connect(args, pool=pool) as c:
            row = _work(c)
    else:
        row = _work(conn)

    if row is None:
        io.echo(
            "checkcreatedb: could not resolve current_user in pg_roles",
            level="error",
        )
        return False

    rolcreatedb, rolsuper, rolname = row
    if not (rolcreatedb or rolsuper):
        io.echo(
            f"current user '{rolname}' lacks CREATEDB privilege; "
            f"cannot create database '{args.databasename}'",
            level="error",
        )
        io.echo(
            f"startup aborted; grant CREATEDB to '{rolname}' and re-run",
            level="error",
        )
        return False

    if rolsuper:
        io.echo(
            f"checkcreatedb: user '{rolname}' is a superuser",
            level="ok",
        )
    else:
        io.echo(
            f"checkcreatedb: user '{rolname}' has CREATEDB", level="ok"
        )
    return True
