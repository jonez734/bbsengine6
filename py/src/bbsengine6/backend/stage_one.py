from bbsengine6 import io, database

from bbsengine6.backend import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs):
    failcount = 0

    io.echo(f"bbsengine6.backend.stage_one.100: {kwargs=}", level="debug")
    pool = database.getpool(args, database=args.databasename)  # zoid6
    with database.connect(args, pool=pool) as conn:
        for m in (
            "checkextensions",
            "checkengine",
            "checkfunctions",
            "checkclasses",
            "checkflag",
            "bank",
        ):
            result = lib.runmodule(
                args,
                m,
                stage=1,
                package="bbsengine6.backend",
                pool=pool,
                conn=conn,
            )
            if result is not True:
                io.echo(
                    f"stage_one: module {m!r} did not return True "
                    f"(got {result!r}); aborting stage.",
                    level="error",
                )
                failcount += 1
                break
        if failcount == 0:
            conn.commit()
        else:
            conn.rollback()

    lib.hr(failcount)
    return True if failcount == 0 else False
