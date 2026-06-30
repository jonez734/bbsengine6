from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    with database.getpool(args, dbname=args.databasename) as pool:  # zoid6
        with database.connect(args, pool=pool) as conn:
            if lib.checkextensions(args, conn=conn, **kwargs) is False:
                return False

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"bbsengine6.startup.stage_one.100: {conn=}", level="debug")

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"bbsengine6.startup.stage_one.120: {conn=}", level="debug")
            if lib.checkfunctions(args, conn=conn, stage=0, **kwargs) is False:
                conn.rollback()
                return False

        with database.connect(args, pool=pool, **kwargs) as conn:
            io.echo(f"bbsengine6.startup.stage_one.140: {conn=}", level="debug")
            if lib.checkfunctions(args, conn=conn, stage=1, **kwargs) is False:
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

        with database.connect(args, pool=pool, **kwargs) as conn:
            res = lib.checknotifyd(args, conn=conn, **kwargs)
            if res is False:
                conn.rollback()

        with database.connect(args, pool=pool, **kwargs) as conn:
            if lib.checkbank(args, conn=conn, **kwargs) is False:
                conn.rollback()
