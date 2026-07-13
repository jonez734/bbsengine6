"""
Per-member PostgreSQL role provisioning for direct psql access.

Auth is by ident (see handbook/specs/pg-ident-auth.md); the
l_<loginid> roles are created with no password.

  Public surface:

  ensure_role_for_member(args, loginid, *, osuser=None) -> str
      Idempotent. Returns the rolname. Creates the role via
      engine.createpgrole if it doesn't exist yet; updates osuser
      if a row already exists and osuser is provided.

  sync_groups(args, loginid) -> bool
      Calls engine.syncpgrolegroups to bring the member's l_<loginid>
      role's sysop/term/web group memberships in line with the
      member's current flags.
"""

from typing import Any, Optional

from bbsengine6 import database, util


def ensure_role_for_member(
    args: Any,
    loginid: str,
    *,
    osuser: Optional[str] = None,
    **kwargs: Any,
) -> Optional[str]:
    """
    Provision or look up the l_<loginid> role for a member.

    Returns the rolname, or None on failure (in which case a logentry
    is written with the error).

    If a row already exists in engine.pgrole for this member, the
    osuser is updated when one is provided. The existing rolname is
    returned; the role is not recreated.

    New rows go through engine.createpgrole, which:
      - derives the rolname as 'l_' + sanitized(loginid)
      - appends a numeric suffix on collision with any existing
        pg_roles.rolname
      - CREATE ROLE l_xxx LOGIN INHERIT (no password; ident auth)
      - GRANT member TO l_xxx
      - INSERT INTO engine.pgrole (membermoniker, rolname, osuser)
    """
    util.logentry(f"bbsengine6.pgrole.ensure_role_for_member.100: {loginid=!r}")

    conn = kwargs.get("conn")
    if conn is None:
        pool = kwargs.get("pool")
        if pool is None:
            util.logentry("bbsengine6.pgrole.ensure_role_for_member.110: no conn/pool")
            return None
        with database.connect(args, pool=pool) as conn:
            return _ensure_role(args, loginid, osuser, conn=conn)

    return _ensure_role(args, loginid, osuser, conn=conn)


def _ensure_role(
    args: Any,
    loginid: str,
    osuser: Optional[str],
    *,
    conn: Any,
) -> Optional[str]:
    # 1. Resolve moniker from loginid. engine.__member's natural key
    #    is moniker (citext); engine.pgrole.membermoniker references it.
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT moniker FROM engine.__member WHERE loginid = %s",
            (loginid,),
        )
        row = cur.fetchone()
        if row is None:
            util.logentry(
                f"bbsengine6.pgrole._ensure_role.120: no member for loginid={loginid!r}"
            )
            return None
        moniker = row["moniker"]

        # 2. Already have a row?
        cur.execute(
            "SELECT rolname, osuser FROM engine.pgrole WHERE membermoniker = %s",
            (moniker,),
        )
        existing = cur.fetchone()

    if existing is not None:
        rolname = existing["rolname"]
        if osuser is not None and osuser != existing["osuser"]:
            with database.cursor(conn=conn) as cur:
                cur.execute(
                    "UPDATE engine.pgrole SET osuser = %s WHERE membermoniker = %s",
                    (osuser, moniker),
                )
            util.logentry(
                f"bbsengine6.pgrole._ensure_role.140: updated osuser for {loginid=}"
            )
        return rolname

    # 3. New row. engine.createpgrole handles role-name derivation,
    #    collision-suffixing, CREATE ROLE, GRANT member, INSERT.
    with database.cursor(conn=conn) as cur:
        cur.execute(
            "SELECT engine.createpgrole(%s, %s) AS rolname",
            (loginid, osuser),
        )
        row = cur.fetchone()
    if row is None or row.get("rolname") is None:
        util.logentry(
            f"bbsengine6.pgrole._ensure_role.160: createpgrole returned NULL for {loginid=}"
        )
        return None
    rolname = row["rolname"]
    util.logentry(
        f"bbsengine6.pgrole._ensure_role.180: created {rolname=} for {loginid=}"
    )
    return rolname


def sync_groups(args: Any, loginid: str, **kwargs: Any) -> bool:
    """
    Sync the l_<loginid> role's group memberships (sysop, term, web)
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

    try:
        with database.cursor(conn=conn) as cur:
            cur.execute(
                "SELECT engine.syncpgrolegroups(%s)",
                (row["membermoniker"],),
            )
        conn.commit()
        return True
    except Exception as e:
        util.logentry(
            f"bbsengine6.pgrole._sync_groups.200: {loginid=!r} error={e}"
        )
        conn.rollback()
        return False
