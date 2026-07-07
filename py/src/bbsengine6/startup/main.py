import psycopg

from bbsengine6 import io, database, util

from . import lib


def init(args, **kwargs) -> bool:
    return True


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def main(args, **kwargs) -> bool:
    def _runstage(args, name, **kwargs):
        pkg = lib.BACKEND_STAGES.get(name)
        if pkg is not None:
            kwargs.setdefault("package", pkg)
        # Dispatch via lib.runmodule (NOT lib.runstage / module.run
        # directly) so that tests patching ``bbsengine6.startup.lib.runmodule``
        # continue to intercept stage calls. Treat only literal True
        # as success; the previous ``is not False`` check silently
        # treated None as success, swallowing SystemExit / parse errors.
        result = lib.runmodule(args, name, **kwargs)
        return result is True

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
        for s in lib.BACKEND_STAGE_NAMES:
            if _runstage(args, s, conn=conn, **stage_kwargs) is False:
                failcount += 1
                pkg = lib.BACKEND_STAGES.get(s, "bbsengine6.startup")
                io.echo(f" module {s} failed (package={pkg!r}) ", level="error")
                break

        if failcount > 0:
            io.echo("bbsengine6 startup failed", level="error")
            conn.rollback()
            return False

        io.echo("bbsengine6 startup complete", level="ok")
        conn.commit()
        return True

    io.echo(f"bbsengine6.startup.120: trace", level="debug")
    conn = kwargs.pop("conn", None)
    # Do NOT log the connection repr here; psycopg.Connection.__repr__
    # includes the DSN, which carries the password. Log only the
    # connection's identity.
    io.echo(f"bbsengine6.startup.125: conn id={id(conn) if conn is not None else None}", level="debug")
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
            except (
                ConnectionError, TimeoutError, OSError, psycopg.OperationalError
            ) as e:
                # Catch network-/socket-level errors and the
                # "database does not exist" OperationalError that
                # getpool() raises when the target database is missing.
                # Both indicate "admin pool unavailable for a reason
                # that startup can recover from by routing through
                # stage_zero / checkcreatedb". A broad `except
                # Exception` would also mask real programming bugs
                # (NameError, TypeError, etc.) as "pool is None" and
                # continue, hiding the failure.
                io.echo(
                    f"bbsengine6.startup.100: pool is None ({e})",
                    level="error",
                )
                return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
