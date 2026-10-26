"""
Show a member's psql access info (rolname, the OS login = loginid, connect command).

Auth is by ident: members connect to PostgreSQL as the OS user
the loginid is the OS login; pg_ident.conf on the DB host
maps that OS user to the m_<moniker> PG role.

No password is ever displayed or stored by this module. If the member
needs to change which OS user they connect from, the welcome-flow
prompt (or a sysop UPDATE on engine.pgrole) is the path.
"""

import sys
from typing import Optional

from bbsengine6 import database, io, util
from bbsengine6 import member as libmember


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return None


def access(args, op: str, **kwargs):
    return True


def main(args, loginid: Optional[str] = None, **kwargs):
    """
    Show psql access info for the given loginid, or for the current
    member if loginid is None.

    - If no engine.pgrole row exists: tell the member to ask a sysop
      to approve them.
    - If last_ack_at IS NULL: render the welcome block, prompt for
      ENTER, then update last_ack_at and (if blank) prompt for the
      OS username.
    - If last_ack_at is set: render the same block but skip the
      acknowledgment prompt.
    """
    target_loginid = loginid
    if target_loginid is None:
        target_loginid = libmember.getcurrentloginid(args, **kwargs)
    if not target_loginid:
        io.echo("no loginid (not logged in?)", level="error")
        return False

    pool = kwargs.get("pool")
    if pool is None:
        io.echo("bbsengine6.console.showpgrole.110: no pool", level="error")
        return False

    with database.connect(args, pool=pool) as conn:
        row = _fetch(args, target_loginid, conn=conn)
        if row is None:
            io.echo(
                f"{{var:labelcolor}}no psql access provisioned for "
                f"{{var:valuecolor}}{target_loginid}{{var:labelcolor}}."
            )
            io.echo(
                f"{{var:labelcolor}}ask a sysop to approve you; once approved,"
            )
            io.echo(
                f"{{var:labelcolor}}the [P] psql credentials option will show your rolname."
            )
            return True

        _render(row, target_loginid)

        # Welcome flow is interactive; skip it when stdin is not a TTY
        # (cron, scripts, etc.) so this module is safe in non-TTY contexts.
        if not sys.stdin.isatty():
            io.echo(
                f"{{var:labelcolor}}non-interactive session; skipping the welcome prompt",
                level="info",
            )
            return True

        # Welcome flow: if last_ack_at is NULL, require acknowledgment
        # and record that the member has read it.
        if row.get("last_ack_at") is None:
            io.echo(
                f"{{var:labelcolor}}press ENTER to acknowledge you have read this"
                f"{{var:inputcolor}}"
            )
            io.inputstring(f"{{var:promptcolor}}{{var:inputcolor}}", "", noneok=True)
            with database.cursor(conn=conn) as cur:
                cur.execute(
                    "UPDATE engine.pgrole SET last_ack_at = now() "
                    "WHERE loginid = %s",
                    (row["loginid"],),
                )
            conn.commit()
            io.echo(f"{{var:okcolor}}acknowledged.")
            row["last_ack_at"] = "now()"

    return True


def _fetch(args, loginid: str, *, conn) -> Optional[dict]:
    with database.cursor(conn=conn) as cur:
        cur.execute(
            """
            SELECT mm.moniker AS membermoniker,
                   mm.loginid,
                   pr.rolname,
                   pr.created_at,
                   pr.last_ack_at
              FROM engine.__member mm
              LEFT JOIN engine.pgrole pr ON pr.membermoniker = mm.moniker
             WHERE mm.loginid = %s
            """,
            (loginid,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    if row.get("rolname") is None:
        return None
    return row


def _render(row: dict, loginid: str) -> None:
    util.heading(f"psql access for {loginid}")
    io.echo(f"{{var:labelcolor}}PG role:     {{var:valuecolor}}{row['rolname']}")
    io.echo(f"{{var:labelcolor}}OS user:     {{var:valuecolor}}{row['loginid']}")
    if row.get("created_at"):
        io.echo(
            f"{{var:labelcolor}}created:     {{var:valuecolor}}{row['created_at']}"
        )
    if row.get("last_ack_at"):
        io.echo(
            f"{{var:labelcolor}}last ack:    {{var:valuecolor}}{row['last_ack_at']}"
        )
    io.echo("")
    # Members log in as their login role (the OS username). The data role is NOLOGIN and
    # is reached only by SET ROLE, so it is never a connect target.
    io.echo(f"{{var:labelcolor}}Connect with:")
    io.echo(
        f"{{var:valuecolor}}  psql -h 127.0.0.1 -U {row['loginid']} -d <dbname>"
    )
    io.echo("")
    io.echo(
        f"{{var:labelcolor}}(no password -- authentication is by ident. Your"
    )
    io.echo(
        f"{{var:labelcolor}}local OS username must match the login role above.)"
    )
