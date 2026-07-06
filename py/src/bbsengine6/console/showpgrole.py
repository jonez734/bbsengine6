"""
Show a member's psql access info (rolname, osuser, connect command).

Auth is by ident: members connect to PostgreSQL as the OS user
recorded in engine.pgrole.osuser, and pg_ident.conf on the DB host
maps that OS user to the l_<loginid> PG role.

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
                "{{var:labelcolor}}ask a sysop to approve you; once approved,"
            )
            io.echo(
                "{{var:labelcolor}}the [P] psql credentials option will show your rolname."
            )
            return True

        _render(row, target_loginid)

        # Welcome flow is interactive; skip it when stdin is not a TTY
        # (cron, scripts, etc.) so this module is safe in non-TTY contexts.
        if not sys.stdin.isatty():
            io.echo(
                "{{var:labelcolor}}non-interactive session; skipping welcome/osuser prompts",
                level="info",
            )
            return True

        # Welcome flow: if last_ack_at is NULL, require acknowledgment
        # and capture the osuser if it isn't set yet.
        if row.get("last_ack_at") is None:
            io.echo(
                "{{var:labelcolor}}press ENTER to acknowledge you have read this"
                "{{var:inputcolor}}"
            )
            io.inputstring("{{var:promptcolor}}{{var:inputcolor}}", "", noneok=True)
            with database.cursor(conn=conn) as cur:
                cur.execute(
                    "UPDATE engine.pgrole SET last_ack_at = now() WHERE memberid = %s",
                    (row["memberid"],),
                )
            conn.commit()
            io.echo("{{var:okcolor}}acknowledged.")
            row["last_ack_at"] = "now()"

        if not row.get("osuser"):
            osuser = io.inputstring(
                "{{var:promptcolor}}enter the OS username you connect from "
                "(or leave blank to skip): {{var:inputcolor}}",
                "",
                noneok=True,
            )
            if osuser:
                with database.cursor(conn=conn) as cur:
                    cur.execute(
                        "UPDATE engine.pgrole SET osuser = %s WHERE memberid = %s",
                        (osuser, row["memberid"]),
                    )
                conn.commit()
                io.echo(
                    f"{{var:okcolor}}recorded osuser={osuser}; ask a sysop to add"
                )
                io.echo(
                    f"{{var:okcolor}}a 'bbbsmap' line to pg_ident.conf (see"
                )
                io.echo("{{var:okcolor}}handbook/specs/pg-ident-auth.md).")
    return True


def _fetch(args, loginid: str, *, conn) -> Optional[dict]:
    with database.cursor(conn=conn) as cur:
        cur.execute(
            """
            SELECT mm.id AS memberid,
                   mm.moniker,
                   mm.loginid,
                   pr.rolname,
                   pr.osuser,
                   pr.created_at,
                   pr.last_ack_at
              FROM engine.__member mm
              LEFT JOIN engine.pgrole pr ON pr.memberid = mm.id
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
    osuser = row.get("osuser") or "(not set)"
    io.echo(f"{{var:labelcolor}}OS user:     {{var:valuecolor}}{osuser}")
    if row.get("created_at"):
        io.echo(
            f"{{var:labelcolor}}created:     {{var:valuecolor}}{row['created_at']}"
        )
    if row.get("last_ack_at"):
        io.echo(
            f"{{var:labelcolor}}last ack:    {{var:valuecolor}}{row['last_ack_at']}"
        )
    io.echo("")
    io.echo("{{var:labelcolor}}Connect with:")
    io.echo(
        f"{{var:valuecolor}}  psql -h 127.0.0.1 -U {row['rolname']} -d <dbname>"
    )
    io.echo("")
    io.echo(
        "{{var:labelcolor}}(no password -- authentication is by ident. Your"
    )
    io.echo(
        "{{var:labelcolor}}local OS username must match the 'osuser' above,"
    )
    io.echo(
        "{{var:labelcolor}}and pg_ident.conf on the DB host must have a"
    )
    io.echo(
        "{{var:labelcolor}}'bbbsmap' line mapping that OS user to the PG role.)"
    )
