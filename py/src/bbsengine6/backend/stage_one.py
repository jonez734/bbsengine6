from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    failcount = 0

    io.echo(f"bbsengine6.backend.stage_one.100: {kwargs=}", level="debug")
    pool = database.getpool(args, database=args.databasename)  # zoid6
    with database.connect(args, pool=pool) as conn:
        for m in ("checkextensions", "checkfunctions", "checkclasses", "checkflag", "bank"):
            if lib.runmodule(
                args,
                m,
                stage=1,
                package="bbsengine6.backend",
                pool=pool,
                conn=conn,
            ) is False:
                failcount += 1
                break
            else:
                lib.ok()
        if failcount == 0:
            conn.commit()
        else:
            conn.rollback()

    lib.hr(failcount)
    return True if failcount == 0 else False
