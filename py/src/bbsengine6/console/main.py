"""Interactive console menu for the BBS engine."""

from bbsengine6 import session, util, io, database, member

from . import lib



def _schema_ready(conn) -> bool:
    """True when the engine member view exists (the bootstrap has reached it).

    The console reads engine.member on every loop. On a database whose
    bootstrap stopped early that view is absent, and the raw SQL error hides
    the cause. Check once, up front, and report it plainly.
    """
    with conn.cursor() as cur:
        cur.execute("select to_regclass('engine.member') is not null")
        return bool(cur.fetchone()[0])

def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def main(args, **kwargs):
    parser = buildargs(args)
    args = parser.parse_args()

    if args.require_registration is True:
        from bbsengine6.module import set_require_registration

        set_require_registration(True)
        io.echo("registration enforcement enabled", level="info")

    io.echo(f"bbsengine.con.main.400: {kwargs=}", level="debug")

    with database.getpool(args) as pool:
        io.echo(f"con.main.main.100: {pool=}", level="debug")
        with database.connect(args, pool=pool, auto_commit=False) as conn:
            io.echo(f"con.main.main.120: {pool=} {conn=}", level="debug")
            if not _schema_ready(conn):
                io.echo(
                    f"database {args.databasename!r} is not bootstrapped "
                    "(engine.member is missing). Run the startup bootstrap "
                    "for this database first.",
                    level="error",
                )
                return False
            if session.start(args, conn=conn, **kwargs) is False:
                io.echo("con.main.140: did not start session", level="error")
                return False

            done = False
            while not done:
                membercount = member.count(args, conn=conn)
                if membercount is not None and membercount > 0:
                    sessionid = session.getcurrentsessionid()
                    if sessionid is not None:
                        session.updatelastactivity(
                            args, sessionid, conn=conn, **kwargs
                        )
                else:
                    io.echo("no session", level="warn")

                util.heading("bbsengine6 console")
                io.echo(
                    f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}{{var:labelcolor}}:{{var:valuecolor}}{args.databaseport}{{f6}}"
                )

                io.echo("{var:optioncolor}[M]{var:labelcolor} Members")
                io.echo("{var:optioncolor}[S]{var:labelcolor} Sessions")
                io.echo("{var:optioncolor}[A]{var:labelcolor} Approvals")
                io.echo("{f6}{var:optioncolor}[X]{var:labelcolor} Exit{f6}")
                ch = io.inputchoice(
                    "{var:promptcolor}console: {var:inputcolor}",
                    "ASMXQ",
                    "X",
                    conn=conn,
                    args=args,
                    pool=pool,
                    **kwargs,
                )
                if ch == "M":
                    io.echo("Members")
                    lib.runmodule(args, "member", pool=pool, **kwargs)
                    continue
                elif ch == "S":
                    io.echo("Sessions")
                    lib.runmodule(args, "session", pool=pool, **kwargs)
                    continue
                elif ch == "A":
                    io.echo("Member Approval")
                    lib.runmodule(args, "memberapproval", pool=pool, **kwargs)
                elif ch == "Q" or ch == "X":
                    io.echo("Exit")
                    break
                else:
                    io.echo("{bell}", end="", flush=True)
                    continue
    return True
