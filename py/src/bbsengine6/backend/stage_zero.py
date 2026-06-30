import psycopg
from bbsengine6 import io, database, util

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    util.heading("stage_zero")

    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo("could not connect to 'postgres'", level="error")
        return False

    with pool:  # postgres
        try:
            with database.connect(args, pool=pool, **kwargs) as conn:
                if lib.checkroles(args, conn=conn, **kwargs) is False:
                    io.echo("checkroles() failed", level="error")
                    return False

                res = lib.checkfunctions(args, conn=conn, stage=0, **kwargs)
                if res is False:
                    io.echo("checkfunctions() failed", level="error")
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
            io.echo_traceback(f"con.main.stage_zero.100: error: {e}")

    io.echo("stage zero complete", level="ok")
    return True
