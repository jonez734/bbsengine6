"""
Per-member PostgreSQL role provisioning.

Public surface:

  ensure_login_role(args, moniker, **kwargs) -> str
      Idempotent. Creates a LOGIN PostgreSQL role named m_<moniker>.
      Grants the 'member' group role and USAGE on the engine schema.
      Inserts a tracking row into engine.pgrole.
      Returns the rolname on success.

  sync_groups(args, loginid) -> bool
      Calls engine.syncpgrolegroups to bring the member's m_<moniker>
      role's sysop/term/web group memberships in line with the
      member's current flags.
"""

from typing import Any, Optional
import re

from bbsengine6 import database, util


def ensure_login_role(args: Any, moniker: str, **kwargs: Any) -> Optional[str]:
    """
    Create a LOGIN PostgreSQL role named m_<moniker>.

    Idempotent: if the role already exists or a pgrole row exists, this
    is a no-op.  Grants the 'member' group role and USAGE on the engine
    schema.  Inserts a tracking row into engine.pgrole with
    rolname = m_<moniker>.

    Returns the rolname on success, or None on failure.
    """
    util.logentry(f"bbsengine6.pgrole.ensure_login_role.100: {moniker=!r}")

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            util.logentry(
                "bbsengine6.pgrole.ensure_login_role.110: no conn/pool"
            )
            return None
        with database.connect(args, pool=pool) as conn:
            return _ensure_login_role(args, moniker, conn=conn)

    return _ensure_login_role(args, moniker, conn=conn)


def role_name_for(moniker: str) -> str:
    """The PostgreSQL role for a new member: m_<moniker>, sanitized to [a-z0-9_].

    An existing engine.pgrole row takes precedence, so a member whose role
    predates this rule keeps it (zoid6's jam maps to role jam).
    """
    return "m_" + re.sub(r"[^a-zA-Z0-9_]", "_", moniker).lower()


def lookup_login_role(args: Any, moniker: str, *, conn: Any) -> Optional[str]:
    """The member's existing database role from engine.pgrole, or None.

    Read-only. This never creates a role or a tracking row, so it is safe on a
    request path: a member with no row is refused rather than provisioned.
    """
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT rolname FROM engine.pgrole WHERE membermoniker = %s",
            (moniker,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return row["rolname"] if isinstance(row, dict) else row[0]


def _reconcile_nologin(args: Any, rolname: str, *, conn: Any) -> None:
    """Make an existing data role NOLOGIN, so only SET ROLE reaches it.

    Data roles were created LOGIN before this rule. A LOGIN data role lets an OS account
    of that name connect directly and skip the login role. Superusers are never altered
    (the connecting role may not ALTER them, and jam is the legacy owner mapping).
    """
    if not database.rolexists(args, rolname, conn=conn):
        return
    privs = database.get_role_privs(args, rolname, conn=conn)
    if privs is None or privs.get("rolsuper") is True:
        return
    if privs.get("rolcanlogin") is True:
        from psycopg import sql as pg_sql

        with database.cursor(conn=conn) as cur:
            cur.execute(pg_sql.SQL("ALTER ROLE {} NOLOGIN").format(pg_sql.Identifier(rolname)))
        util.logentry(f"bbsengine6.pgrole._reconcile_nologin.100: set NOLOGIN on {rolname=}")


def _ensure_login_role(args: Any, moniker: str, *, conn: Any) -> Optional[str]:
    rolname = role_name_for(moniker)

    # 1. Check if a pgrole row already exists for this member.
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT rolname FROM engine.pgrole WHERE membermoniker = %s",
            (moniker,),
        )
        existing = cur.fetchone()

    if existing is not None:
        util.logentry(
            f"bbsengine6.pgrole._ensure_login_role.140: "
            f"pgrole row exists for {moniker=}, rolname={existing['rolname']}"
        )
        _reconcile_nologin(args, existing["rolname"], conn=conn)
        return existing["rolname"]

    # 2. Check if the PostgreSQL role already exists (e.g. created via psql).
    if not database.rolexists(args, rolname, conn=conn):
        ok = database.createrol(
            args,
            rolname,
            conn=conn,
            login=False,
            superuser=False,
            createdb=False,
            createrole=False,
        )
        if not ok:
            util.logentry(
                f"bbsengine6.pgrole._ensure_login_role.160: "
                f"createrol failed for {rolname=}"
            )
            return None
    else:
        _reconcile_nologin(args, rolname, conn=conn)

    # 3. Grant the 'member' group role.
    # rolname is regex-sanitized to [A-Za-z0-9_]+ so it's safe to splice,
    # but use sql.Identifier for defense in depth.
    from psycopg import sql as pg_sql

    with database.cursor(conn=conn) as cur:
        cur.execute(
            pg_sql.SQL("GRANT member TO {}").format(pg_sql.Identifier(rolname))
        )

    # 4. Grant USAGE on the engine schema.
    database.manage_schema_priv(
        args, "grant", "usage", "engine", rolname, conn=conn
    )

    # 5. Insert tracking row into engine.pgrole.
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "INSERT INTO engine.pgrole (membermoniker, rolname, created_at) "
            "VALUES (%s, %s, now()) "
            "ON CONFLICT (membermoniker) DO NOTHING",
            (moniker, rolname),
        )

    util.logentry(
        f"bbsengine6.pgrole._ensure_login_role.180: "
        f"created {rolname=} for {moniker=}"
    )
    return rolname


_PLAIN_NAME = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def ensure_os_login_role(
    args: Any, osuser: str, member_role: str, *, conn: Any
) -> bool:
    """Create the OS-user login role and let it SET ROLE into the member's role.

    ident (no pg_ident map) logs a connection in as the role named like the OS user.
    That login role is created NOINHERIT: it holds no privileges of its own and acts
    only through ``SET ROLE <member_role>``, which requires membership in it.

    Returns True when the role exists and is granted membership, False otherwise.
    Refuses an osuser that is not a plain lowercase name, and refuses the member role
    itself as the login role. Nothing is created in either refused case.
    """
    util.logentry(f"bbsengine6.pgrole.ensure_os_login_role.100: {osuser=!r} {member_role=!r}")

    if not _PLAIN_NAME.match(osuser or ""):
        util.logentry(f"bbsengine6.pgrole.ensure_os_login_role.110: refused osuser {osuser!r}")
        return False
    if osuser == member_role:
        util.logentry("bbsengine6.pgrole.ensure_os_login_role.120: osuser is the member role")
        return False

    if not database.rolexists(args, osuser, conn=conn):
        ok = database.createrol(
            args,
            osuser,
            conn=conn,
            login=True,
            inherit=False,
            superuser=False,
            createdb=False,
            createrole=False,
        )
        if not ok:
            util.logentry(
                f"bbsengine6.pgrole.ensure_os_login_role.130: createrol failed for {osuser!r}"
            )
            return False

    from psycopg import sql as pg_sql

    with database.cursor(conn=conn) as cur:
        cur.execute(
            pg_sql.SQL("GRANT {} TO {}").format(
                pg_sql.Identifier(member_role), pg_sql.Identifier(osuser)
            )
        )
    return True


def sync_groups(args: Any, loginid: str, **kwargs: Any) -> bool:
    """
    Sync the m_<moniker> role's group memberships (sysop, term, web)
    to the member's current flags. Idempotent and safe to call after
    any flag change.

    Returns True on success, False if the member is not found, the
    role is not yet provisioned, or the SQL call fails.
    """
    util.logentry(f"bbsengine6.pgrole.sync_groups.100: {loginid=!r}")

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            util.logentry("bbsengine6.pgrole.sync_groups.110: no conn/pool")
            return False
        with database.connect(args, pool=pool) as conn:
            return _sync_groups(args, loginid, conn=conn)

    return _sync_groups(args, loginid, conn=conn)


def _sync_groups(args: Any, loginid: str, *, conn: Any) -> bool:
    # Look up the membermoniker and the rolename. If either is missing
    # there's nothing to sync.
    with database.cursor(conn=conn) as cur:
        cur.execute(
            """
            SELECT mm.moniker AS membermoniker, pr.rolname
              FROM engine.__member mm
              JOIN engine.pgrole pr ON pr.membermoniker = mm.moniker
             WHERE mm.loginid = %s
            """,
            (loginid,),
        )
        row = cur.fetchone()
    if row is None:
        util.logentry(
            f"bbsengine6.pgrole._sync_groups.140: no pgrole for {loginid=!r}"
        )
        return False

    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT engine.syncpgrolegroups(%s)",
            (row["membermoniker"],),
        )
    return True
