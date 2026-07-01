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
    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo("could not connect to 'postgres'", level="error")
        return False

    with pool:  # postgres
        try:
            with database.connect(args, pool=pool, **kwargs) as conn:
                for m in ("checkroles", "checkfunctions", "checksuperuser", "checkwebserverrole", "checkdatabase"):
                    io.echo(f"{{labelcolor}}module {{valuecolor}}{m}{{labelcolor}}: ", end="")
                    if module.run(args, m, conn=conn, package="bbsengine6.backend", stage=0, **kwargs) is True:
                        io.echo(f"{{level.ok}} ok ")
                    else:
                        io.echo(f"{{level.error}}fail{{f6}}{util.hr(color='level.fail')}")
                        failcount += 1
                        break
        except Exception as e:
            io.echo_traceback(f"backend.stage_zero.100: error: {e}")
        finally:
            if failcount == 0:
                io.echo(f"bbsengine6.backend.stage_zero.120: complete")
                util.hr()
                conn.commit()
            else:
                io.echo(f"bbsengine6.backend.stage_zero.130: {failcount=}", level="error")
                util.hr(color=f"{{level.error}}")
                conn.rollback()

            return True if failcount == 0 else False

