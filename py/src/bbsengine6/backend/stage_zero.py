from bbsengine6 import io, database, util

from . import lib

def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    util.heading("stage_zero")

    failcount = 0

    # Build the admin pool against 'postgres' first; both
    # checkdatabase and the inner sub-step loop need it. The caller
    # (startup.main) only passes conn, so we build the pool here.
    pool = database.getpool(args, dbname="postgres")
    if pool is None:
        io.echo("could not connect to 'postgres'", level="error")
        return False

    with pool:  # postgres
        try:
            with database.connect(args, pool=pool) as conn:
                # checkcreatedb MUST run before checkdatabase so that
                # a missing CREATEDB privilege is detected with a
                # clear two-line error before we attempt CREATE
                # DATABASE (which would surface as a raw psycopg
                # InsufficientPrivilege traceback).
                for m in (
                    "checkcreatedb",
                    "checkdatabase",
                    "checkextensions",
                    "checkroles",
                    "checkfunctions",
                    "checksuperuser",
                    "checkwebserverrole",
                    "checkengine",
                ):
                    result = lib.runmodule(
                        args,
                        m,
                        package="bbsengine6.backend",
                        stage=0,
                        pool=pool,
                        conn=conn,
                    )
                    if result is not True:
                        io.echo(
                            f"stage_zero: module {m!r} did not return True "
                            f"(got {result!r}); aborting stage.",
                            level="error",
                        )
                        failcount += 1
                        break
        except Exception as e:
            io.echo_traceback(f"backend.stage_zero.100: error: {e}")
            failcount += 1
        finally:
            if failcount == 0:
                io.echo(f"bbsengine6.backend.stage_zero.120: complete", level="ok")
            else:
                io.echo(f"bbsengine6.backend.stage_zero.130: {failcount=}", level="error")

    return True if failcount == 0 else False
