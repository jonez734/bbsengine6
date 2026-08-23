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
            "checkclasses",
            # Phase 1+ password hardening: install
            # chk_member_password_bcrypt on engine.__member and audit
            # the column for any legacy $1$ MD5-crypt rows. Runs every
            # startup so operators no longer need to manually
            # ``psql \i bbsengine6.sql`` to land the constraint. The
            # audit log line is the operator signal during the
            # migration window; once the column is clean the warning
            # becomes a green-bg ``0 row(s)``.
            "checkpasswordformat",
            "checkfunctions",
            # Phase 1 fix: stage_one's checkfunctions re-CREATEs the
            # 5 public.* SECURITY DEFINER helpers in the target DB,
            # which resets their owner to the connecting user (typically
            # the bootstrap superuser). Without this follow-up,
            # stage_zero's checkzoid6owner (which runs against the
            # admin 'postgres' DB) reassigns the helpers to zoid6
            # there, but the target DB's copies stay owned by the
            # bootstrap principal — breaking the trust model that
            # database.verify_function_owner and casino.startup.
            # checkcasino both depend on. Run checkzoid6owner here so
            # the target DB's copies are reassigned to zoid6 before
            # any other module issues GRANTs through them.
            "checkzoid6owner",
            "checkmemberflag",
            "checkmessage",
            "checkbank",
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
