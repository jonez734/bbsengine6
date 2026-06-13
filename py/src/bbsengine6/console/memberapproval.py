"""
Approve pending member applications.

Allows sysops to review and approve member applications that are pending approval.
Requires SYSOP flag to access this module.
"""

from bbsengine6 import util, member, database, io


def init(args, **kw: dict) -> bool:
    return True


def access(args, op: str, **kw: dict) -> bool:
    return member.checkflag(args, "SYSOP", member.getcurrentid(args))


def buildargs(args, **kw: dict):
    #    return lib.buildargs(args, **kw)
    return None


def main(args, **kw):
    util.heading("member approval")
    sql = "select moniker from engine.member where approvedbymoniker is null"
    dat = ()

    currentmoniker = member.getcurrentmoniker(args)

    with database.connect(args) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, dat)
            if cur.rowcount == 0:
                io.echo("no members waiting for approval")
                return True

            res = cur.fetchmany()
            for rec in res:
                m = member.getbymoniker(args, rec["moniker"])
                if m is None:
                    io.echo("You do not exist! Go away!", level="error")
                    return False

                moniker = m["moniker"]

                io.echo(f"{m=}")
                io.echo(
                    f"{{labelcolor}}Moniker: {{valuecolor}}{moniker} {{labelcolor}}({{valuecolor}}{m['loginid']}{{labelcolor}})"
                )
                io.echo(
                    f"{{labelcolor}}E-Mail:  {{valuecolor}}{m['email']} {{labelcolor}}",
                    end="",
                )
                if member.checkflag(args, "EMAILVERIFIED", moniker=moniker) is True:
                    io.echo(
                        " (verified)"
                    )
                else:
                    io.echo(" (not verified)")
                util.hr()
                if (
                    io.inputboolean(
                        "{var:promptcolor}is this email address verified? {var:optioncolor}[Yn]{var:promptcolor}: {var:inputcolor}",
                        "Y",
                    )
                    is True
                ):
                    with database.connect(args, **kw) as txn_conn:
                        try:
                            member.setflag(
                                args,
                                "EMAILVERIFIED",
                                True,
                                moniker=moniker,
                                conn=txn_conn,
                            )
                            txn_conn.commit()
                        except Exception as e:
                            io.echo_traceback(f"bbsengine6.console.memberapproval: {e}")
                            txn_conn.rollback()
                else:
                    with database.connect(args, **kw) as txn_conn:
                        try:
                            member.setflag(
                                args,
                                "EMAILVERIFIED",
                                False,
                                moniker=moniker,
                                conn=txn_conn,
                            )
                            m["dateemailverified"] = "now()"
                            m["emailverifiedbymoniker"] = currentmoniker
                            txn_conn.commit()
                        except Exception as e:
                            io.echo_traceback(f"bbsengine6.console.memberapproval: {e}")
                            txn_conn.rollback()
                if (
                    io.inputboolean(
                        "{var:promptcolor}approve this member? {var:optioncolor}[Yn]{var:promptcolor}: {var:inputcolor}",
                        "Y",
                    )
                    is True
                ):
                    with database.connect(args, **kw) as txn_conn:
                        try:
                            member.setflag(
                                args, "APPROVED", True, moniker=moniker, conn=txn_conn
                            )
                            m["approvedbymoniker"] = currentmoniker
                            m["dateapproved"] = "now()"
                            member.update(args, m, m["moniker"], conn=txn_conn)
                            txn_conn.commit()
                        except Exception as e:
                            io.echo_traceback(f"bbsengine6.console.memberapproval: {e}")
                            txn_conn.rollback()
                else:
                    with database.connect(args, **kw) as txn_conn:
                        try:
                            member.setflag(
                                args, "APPROVED", False, moniker=moniker, conn=txn_conn
                            )
                            txn_conn.commit()
                        except Exception as e:
                            io.echo_traceback(f"bbsengine6.console.memberapproval: {e}")
                            txn_conn.rollback()
    return True
