import psycopg
from bbsengine6 import io, database, util

from . import lib

def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    util.heading("stage_zero")

    failcount = 0

    if lib.runmodule(args, "checkdatabase", **kwargs) is False:
        failcount += 1
        return False

    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo("could not connect to 'postgres'", level="error")
        lib.hr(1)
        return False

    with pool:  # postgres
        try:
            with database.connect(args, pool=pool) as conn:
                for m in (
                    "checkcreatedb",
                    "checkextensions",
                    "checkroles",
                    "checkfunctions",
                    "checksuperuser",
                    "checkwebserverrole",
                    "checkengine",
                ):
                    if lib.runmodule(
                        args,
                        m,
                        package="bbsengine6.backend",
                        stage=0,
                        pool=pool,
                        conn=conn,
                    ) is False:
                        failcount += 1
                        break
        except Exception as e:
            io.echo_traceback(f"backend.stage_zero.100: error: {e}")
        finally:
            if failcount == 0:
                io.echo(f"bbsengine6.backend.stage_zero.120: complete", level="ok")
            else:
                io.echo(f"bbsengine6.backend.stage_zero.130: {failcount=}", level="error")

    lib.hr(failcount)
    return True if failcount == 0 else False
