import psycopg

from bbsengine6 import session, util, io, database, member  # type: ignore
# import bbsengine6 as bbsengine

from . import lib


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
        with database.connect(args, pool=pool) as conn:
            io.echo(f"con.main.main.120: {pool=} {conn=}", level="debug")
            conn.autocommit = False
            if session.start(args, conn=conn, **kwargs) is False:
                io.echo(f"con.main.140: did not start session", level="error")
                return False

            done = False
            while not done:
                membercount = member.count(args, conn=conn)
                if membercount is not None and membercount > 0:
                    sessionid = session.getcurrentsessionid()  # type: ignore
                    if sessionid is not None:
                        session.updatelastactivity(args, sessionid, conn=conn, **kwargs)  # type: ignore
                else:
                    io.echo(f"no session", level="warn")

                util.heading("bbsengine6 console")
                io.echo(
                    f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.database} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}{{var:labelcolor}}:{{var:valuecolor}}{args.databaseport}{{f6}}"
                )

                io.echo("{var:optioncolor}[M]{var:labelcolor} Members")
                io.echo("{var:optioncolor}[S]{var:labelcolor} Sessions")
                io.echo("{f6}{var:optioncolor}[X]{var:labelcolor} Exit{f6}")
                ch = io.inputchoice(
                    "{var:promptcolor}console: {var:inputcolor}",
                    "SMXQ",
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
                    lib.runmodule(args, "memberapproval", **kwargs)
                elif ch == "Q" or ch == "X":
                    io.echo("Exit")
                    break
                else:
                    io.echo("{bell}", end="", flush=True)
                    done = True
                    break
        return True
