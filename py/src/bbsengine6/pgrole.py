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


def _ensure_login_role(args: Any, moniker: str, *, conn: Any) -> Optional[str]:
    rolname = "m_" + re.sub(r"[^a-zA-Z0-9_]", "_", moniker).lower()

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
        return existing["rolname"]

    # 2. Check if the PostgreSQL role already exists (e.g. created via psql).
    if not database.rolexists(args, rolname, conn=conn):
        ok = database.createrol(
            args,
            rolname,
            conn=conn,
            login=True,
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

    # 3. Grant the 'member' group role.
    with database.cursor(conn=conn) as cur:
        cur.execute(f'GRANT member TO "{rolname}"')

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
