import psycopg

from bbsengine6 import session, util, io, database, member
# import bbsengine6 as bbsengine

from . import lib


def init(args, **kwargs):
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs):
    return True


def stage_zero(args, **kwargs):
    io.echo("starting stage 0")
    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo("could not connect to 'postgres'", level="error")
        return False

    with pool:  # postgres
        try:
            with database.connect(args, pool=pool, **kwargs) as conn:
                if lib.checkroles(args, conn=conn, **kwargs) is False:
                    io.echo("checkroles() failed", level="debug")
                    return False

                res = lib.checkfunctions(args, conn=conn, stage=0, **kwargs)
                if res is False:
                    return False

                if lib.checksuperuser(args, conn=conn, **kwargs) is False:
                    io.echo(
                        f"{{var:valuecolor}}no permission to create the database",
                        level="error",
                    )
                    return False

                if lib.checkwebserverrole(args, conn=conn, **kwargs) is False:
                    io.echo(
                        f"{{var:labelcolor}}check of {{var:valuecolor}}www-data{{var:labelcolor}} failed",
                        level="error",
                    )
                    return False

                if lib.checkdatabase(args, pool=pool, conn=conn, **kwargs) is False:
                    io.echo("unable to create database", level="error")
                    return False

                conn.commit()
        except psycopg.DatabaseError as e:
            io.echo(f"con.main.stage_zero.100: error: {e}", level="error")

    #  pool = database.getpool(args, dbname=args.databasename)
    #  if pool is None:
    #    io.echo(f"could not connect to '{args.databasename}'", level="error")
    #    return False

    #  with pool:
    #    conn = database.connect(args, pool=pool, **kwargs)
    #    with conn:
    #      res = lib.checkfunctions(args, conn=conn, stage=1, **kwargs)
    #      if res is False:
    #        io.echo("checkfunctions() failed", level="error")
    #        conn.rollback()
    #        return False

    io.echo("stage zero complete", level="ok")
    return True


def stage_one(args, **kwargs):
    with database.getpool(args, dbname=args.databasename) as pool:  # zoid6
        with database.connect(args, pool=pool) as conn:
            if lib.checkextensions(args, conn=conn, **kwargs) is False:
                return False

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"con.main.stage_one.100: {conn=}", level="debug")
            res = lib.checkschema(args, conn=conn, **kwargs)
            if res is True:
                pass
                # io.echo("commit", level="debug")
                # conn.commit()
            elif res is False:
                pass
                # io.echo("rollback", level="debug")
                # conn.rollback()

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"con.main.stage_one.120: {conn=}", level="debug")
            if lib.checkfunctions(args, conn=conn, stage=0, **kwargs) is False:
                io.echo("FAIL")
                conn.rollback()
                return False

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"con.main.stage_one.140: {conn=}", level="debug")
            if lib.checkfunctions(args, conn=conn, stage=1, **kwargs) is False:
                io.echo("FAIL")
                conn.rollback()
                return False

        with database.connect(args, pool=pool, **kwargs) as conn:
            res = lib.checkclasses(args, conn=conn, **kwargs)
            if res is False:
                conn.rollback()

        with database.connect(args, pool=pool, **kwargs) as conn:
            res = lib.checkflag(args, conn=conn, **kwargs)
            if res is False:
                conn.rollback()

        with database.connect(args, pool=pool, **kwargs) as conn:
            res = lib.checknotify(args, conn=conn, **kwargs)
            if res is False:
                conn.rollback()


def main(args, **kwargs):
    parser = buildargs(args)
    args = parser.parse_args()

    io.echo(f"bbsengine.con.main.400: {kwargs=}", level="debug")

    util.heading("engine checks")
    if stage_zero(args, **kwargs) is False:
        io.echo("fail", level="error")
        return False

    if stage_one(args, **kwargs) is False:
        io.echo("fail", level="error")
        return False

    with database.getpool(args) as pool:
        io.echo(f"con.main.main.100: {pool=}", level="debug")
        with database.connect(args, pool=pool) as conn:
            io.echo(f"con.main.main.120: {pool=} {conn=}", level="debug")
            conn.autocommit = False
            if member.count(args, conn=conn) > 0:
                if session.start(args, conn=conn, **kwargs) is False:
                    io.echo(f"con.main.140: did not start session", level="error")
                    return False
            else:
                io.echo("no members, so not starting a session", level="warn")

        done = False
        while not done:
            membercount = member.count(args, conn=conn)
            if membercount > 0:
                session.updatelastactivity(
                    args, session.getcurrentsessionid(), conn=conn, **kwargs
                )
            else:
                io.echo(f"no session", level="warn")

            util.heading("bbsengine6 console")
            io.echo(
                f"{{f6}}{{var:labelcolor}}database: {{var:valuecolor}}{args.databasename} {{var:labelcolor}}host: {{var:valuecolor}}{args.databasehost}{{var:labelcolor}}:{{var:valuecolor}}{args.databaseport}{{f6}}"
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
