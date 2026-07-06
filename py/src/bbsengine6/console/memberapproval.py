"""Approve pending member applications.

Allows sysops to review and approve member applications that are pending
approval. Requires SYSOP flag to access this module.
"""

from bbsengine6 import util, member, database, io
from bbsengine6 import pgrole


def init(args, **kw: dict) -> bool:
    """Module init: nothing to do."""
    return True


def access(args, op: str, **kw: dict) -> bool:
    """Only SYSOPs may approve members."""
    return member.checkflag(args, "SYSOP", member.getcurrentid(args))


def buildargs(args, **kw: dict):
    """No additional CLI args; the menu is interactive only."""
    return None


def _set_email_verified(args, moniker: str, verified: bool, *, conn) -> bool:
    """Symmetric helper: set EMAILVERIFIED flag and stamp the audit columns.

    Both the verified-yes and verified-no paths in the menu call this so
    the dateemailverified/emailverifiedbymoniker audit fields are kept in
    sync regardless of the answer.
    """
    if not member.setflag(
        args, "EMAILVERIFIED", verified, moniker=moniker, conn=conn
    ):
        return False
    database.update(
        args,
        "engine.__member",
        moniker,
        {
            "dateemailverified": "now()",
            "emailverifiedbymoniker": member.getcurrentmoniker(args, conn=conn),
        },
        primarykey="moniker",
        commit=False,
        conn=conn,
    )
    return True


def _approve_member(args, moniker: str, currentmoniker: str, *, conn) -> bool:
    """Set APPROVED, stamp audit columns, provision psql role.

    Returns True on success, False on any failure (in which case the
    caller rolls back the transaction).
    """
    if not member.setflag(
        args, "APPROVED", True, moniker=moniker, conn=conn
    ):
        return False
    if (
        database.update(
            args,
            "engine.__member",
            moniker,
            {
                "approvedbymoniker": currentmoniker,
                "dateapproved": "now()",
            },
            primarykey="moniker",
            commit=False,
            conn=conn,
        )
        is False
    ):
        return False
    return True


def _disapprove_member(args, moniker: str, *, conn) -> bool:
    """Clear APPROVED and the audit columns."""
    if not member.setflag(
        args, "APPROVED", False, moniker=moniker, conn=conn
    ):
        return False
    if (
        database.update(
            args,
            "engine.__member",
            moniker,
            {"approvedbymoniker": None, "dateapproved": None},
            primarykey="moniker",
            commit=False,
            conn=conn,
        )
        is False
    ):
        return False
    return True


def main(args, **kw):
    util.heading("member approval")
    sql = "select moniker from engine.member where approvedbymoniker is null"

    with database.connect(args, auto_commit=False) as conn:
        with database.cursor(conn=conn) as cur:
            cur.execute(sql)
            if cur.rowcount == 0:
                io.echo("no members waiting for approval")
                return True

            # Use fetchall (cur.fetchmany() defaults to arraysize=1
            # in psycopg, which would only process the first row).
            pending = cur.fetchall()

        currentmoniker = member.getcurrentmoniker(args, conn=conn)

        for rec in pending:
            moniker = rec.get("moniker")
            if not moniker:
                io.echo("skipping record with no moniker", level="warn")
                continue

            m = member.getbymoniker(args, moniker, conn=conn)
            if m is None:
                io.echo(
                    f"could not load member for moniker={moniker!r}",
                    level="error",
                )
                continue

            io.echo(
                f"{{labelcolor}}Moniker: {{valuecolor}}{moniker} {{labelcolor}}({{valuecolor}}{m['loginid']}{{labelcolor}})"
            )
            io.echo(
                f"{{labelcolor}}E-Mail:  {{valuecolor}}{m['email']} {{labelcolor}}",
                end="",
            )
            if member.checkflag(
                args, "EMAILVERIFIED", moniker=moniker, conn=conn
            ) is True:
                io.echo(" (verified)")
            else:
                io.echo(" (not verified)")
            util.hr()

            try:
                if io.inputboolean(
                    "{var:promptcolor}is this email address verified? {var:optioncolor}[Yn]{var:promptcolor}: {var:inputcolor}",
                    "Y",
                ):
                    _set_email_verified(args, moniker, True, conn=conn)
                else:
                    _set_email_verified(args, moniker, False, conn=conn)

                if io.inputboolean(
                    "{var:promptcolor}approve this member? {var:optioncolor}[Yn]{var:promptcolor}: {var:inputcolor}",
                    "Y",
                ):
                    if not _approve_member(
                        args, moniker, currentmoniker, conn=conn
                    ):
                        raise RuntimeError(
                            f"approve_member failed for {moniker!r}"
                        )
                    conn.commit()

                    rolname = pgrole.ensure_role_for_member(
                        args, m["loginid"], osuser=None, conn=conn
                    )
                    if rolname is not None:
                        io.echo(
                            f"{{var:labelcolor}}psql access provisioned: "
                            f"{{var:valuecolor}}{rolname} "
                            f"{{var:labelcolor}}(add a 'bbbsmap' line to "
                            f"{{var:valuecolor}}pg_ident.conf{{var:labelcolor}} "
                            f"and reload PG; see handbook/specs/pg-ident-auth.md)"
                        )
                    else:
                        io.echo(
                            "psql role provisioning failed; see logs",
                            level="error",
                        )
                else:
                    if not _disapprove_member(args, moniker, conn=conn):
                        raise RuntimeError(
                            f"disapprove_member failed for {moniker!r}"
                        )
                    conn.commit()
            except Exception as e:
                io.echo_traceback(
                    f"bbsengine6.console.memberapproval.main: {e}"
                )
                conn.rollback()
    return True
