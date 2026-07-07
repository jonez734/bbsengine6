from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def main(args, **kwargs) -> bool:
    def _work(conn):
        failcount = 0
        io.echo(f"{{labelcolor}}database '{{valuecolor}}{args.databasename}{{labelcolor}}': ", end="")
        if (database.exists(args, args.databasename, conn=conn) is True):
            lib.ok()
        else:
            io.echo(f" create ")
            # database.create() requires autocommit on caller-supplied conn
            # (CREATE DATABASE cannot run inside a transaction block).
            prev_autocommit = conn.autocommit
            conn.autocommit = True
            try:
                if (database.create(args, args.databasename, conn=conn, **kwargs) is True):
                    lib.ok()
                else:
                    failcount += 1
                    lib.fail()
            finally:
                conn.autocommit = prev_autocommit

        lib.hr(failcount)
        return True if failcount == 0 else False

    conn = kwargs.get("conn", None)
    return _work(conn)
