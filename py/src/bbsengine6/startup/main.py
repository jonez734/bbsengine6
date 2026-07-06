from bbsengine6 import io, database, util

from . import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs) -> bool:
    def _runstage(args, name, **kwargs):
        return lib.runmodule(args, name, **kwargs) is not False

    def _work(conn):
        util.heading("bbsengine6 startup")
        failcount = 0
        # Drop conn/pool from kwargs so we don't double-pass them to
        # _runstage; _work is always called with a real conn that
        # already represents the active session.
        stage_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ("conn", "pool")
        }
        for s in ("stage_zero", "stage_one", "bank"):
            if _runstage(args, s, conn=conn, **stage_kwargs) is False:
                failcount += 1
                io.echo(f" module {s} failed ", level="error")

        if failcount > 0:
            io.echo("bbsengine6 startup failed", level="error")
            conn.rollback()
            return False

        io.echo("bbsengine6 startup complete", level="ok")
        conn.commit()
        return True

    io.echo(f"bbsengine6.startup.120: trace")
    conn = kwargs.pop("conn", None)
    io.echo(f"{conn=}", level="debug")
    if conn is None:
        pool = kwargs.pop("pool", None)
        if pool is None:
            io.echo(
                "bbsengine6.startup.110: no conn or pool supplied; "
                "attempting admin pool against 'postgres' to recover "
                "missing database",
                level="debug",
            )
            try:
                pool = database.getpool(args, dbname="postgres")
            except Exception as e:
                io.echo(
                    f"bbsengine6.startup.100: pool is None ({e})",
                    level="error",
                )
                return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
