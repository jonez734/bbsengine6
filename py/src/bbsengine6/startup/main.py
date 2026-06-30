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
        for s in ("stage_zero", "stage_one", "engine", "bank"):
            if _runstage(args, s, conn=conn, **kwargs) is False:
                failcount += 1
                io.echo(f" module {s} failed ", level="error")

        if failcount > 0:
            io.echo("bbsengine6 startup failed", level="error")
            conn.rollback()
            return False

        io.echo("bbsengine6 startup complete", level="ok")
        conn.commit()
        return True

    conn = kwargs.get("conn", None)
    io.echo(f"{conn=}", level="debug")
    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo("bbsengine6.startup.100: pool is None", level="error")
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
