import psycopg

from bbsengine6 import io, database, util
from bbsengine6.backend.lib import issysop

from . import lib
from .message_subscription import subscribe_to_bed_sync


# Database name used by stage_zero for the maintenance pool. Every
# PostgreSQL cluster ships with this database, so it is always reachable
# whenever the server is up and the caller has SUPERUSER / CONNECT on it.
_ADMIN_DATABASE = "postgres"


def init(args, **kwargs) -> bool:
    return True


def _maybe_subscribe_to_bed(args, **kwargs) -> bool:
    """Subscribe the current session to bed's server-push messages.

    Reads the current moniker from bbsengine6.member._threadlocal
    (set elsewhere by the auth flow) and, if present, attempts a
    `message_subscribe` against the local bed daemon. Failure is
    non-fatal: getch.py/bottombar.py will fall back to direct DB
    reads on a cold local cache.
    """
    try:
        from bbsengine6.member import _threadlocal

        moniker = getattr(_threadlocal, "moniker", None)
        if not moniker:
            return False
    except Exception:
        io.echo_traceback("bbsengine6.startup.main._maybe_subscribe_to_bed.moniker:")
        return False

    try:
        ok = subscribe_to_bed_sync(args, moniker)
        if ok:
            io.echo(
                f"bbsengine6 startup: subscribed to bed message pushes for {moniker!r}",
                level="info",
            )
        else:
            io.echo(
                "bbsengine6 startup: bed unreachable; using DB-polling "
                "fallback for messages",
                level="debug",
            )
        return ok
    except Exception:
        io.echo_traceback("bbsengine6.startup.main._maybe_subscribe_to_bed:")
        return False


def access(args, op, **kwargs) -> bool:
    # The access check runs before any DB connection is established
    # (e.g. casino's __main__ calls runmodule("startup", ...) before
    # opening a pool). issysop needs a conn/pool to query pg_auth_members;
    # without one it returns False and the whole startup aborts, which is
    # wrong - the conn gets built later inside main(). Treat no-conn as
    # "access granted" and defer the real sysop check to main() once the
    # pool is up. If a conn/pool IS available, defer to issysop so
    # the check still applies when called from a context that has one
    # (e.g. the engine boot path).
    if "conn" not in kwargs and "pool" not in kwargs:
        return True
    return issysop(args, **kwargs)


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def _select_stage_one_pool(
    args,
    caller_pool,
    target_pool_factory,
):
    """Choose the pool to use for stage_one.

    The pre-flight always builds an admin pool against 'postgres' and runs
    stage_zero (which creates the target database if missing). For
    stage_one we need a pool that points at the now-present target
    database.

    Selection rules:

    1. If the caller supplied ``pool=`` via kwargs, sanity-check it:
       try ``pool.getconn()`` to acquire a connection; if it succeeds
       and the connection's ``info.dbname`` matches ``args.databasename``
       the caller's pool is good - return the conn to it and reuse the
       pool for stage_one. If ``info.dbname`` does not match (the
       caller's pool points at e.g. the old 'postgres' admin database
       that no longer exists, or a different application database)
       or if ``getconn()`` raises ``OperationalError`` /
       ``psycopg_pool.PoolTimeout``, fall through and build a fresh
       target pool.

    2. Otherwise, build a fresh target pool via ``target_pool_factory``
       and use that.

    Args:
        args: Application args.
        caller_pool: Pool supplied by the caller via kwargs, or None.
        target_pool_factory: Zero-arg callable that returns a fresh
            pool against ``args.databasename``. Must raise
            ``psycopg.OperationalError`` (or a subclass) if the target
            database is unreachable.

    Returns:
        The pool to use for stage_one.

    Raises:
        psycopg.OperationalError: If the target database cannot be
            reached even after the pre-flight bootstrap. Caller should
            catch this and surface a clear error.
    """
    if caller_pool is not None:
        try:
            check_conn = caller_pool.getconn()
        except (psycopg.OperationalError, OSError) as e:
            io.echo(
                f"bbsengine6.startup.117: caller pool getconn() failed "
                f"({e}); falling back to fresh target pool",
                level="debug",
            )
        else:
            try:
                pool_dbname = getattr(getattr(check_conn, "info", None), "dbname", None)
            except Exception:
                pool_dbname = None
            try:
                caller_pool.putconn(check_conn)
            except Exception:
                io.echo_traceback(
                    "bbsengine6.startup.main._select_stage_one_pool.putconn:"
                )
            if pool_dbname == args.databasename:
                io.echo(
                    f"bbsengine6.startup.118: reusing caller-supplied pool "
                    f"(dbname={pool_dbname!r})",
                    level="debug",
                )
                return caller_pool
            io.echo(
                f"bbsengine6.startup.117: caller-supplied pool points at "
                f"{pool_dbname!r}, expected {args.databasename!r}; "
                f"using fresh target pool",
                level="debug",
            )

    return target_pool_factory()


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

    # Drop conn/pool from kwargs so we don't double-pass them to
    # _runstage; the pool-selection logic below picks the right pool
    # for stage_one explicitly.
    caller_conn = kwargs.pop("conn", None)
    caller_pool = kwargs.pop("pool", None)
    stage_kwargs = {k: v for k, v in kwargs.items() if k not in ("conn", "pool")}

    io.echo(f"bbsengine6.startup.120: trace", level="debug")
    # Do NOT log the connection repr here; psycopg.Connection.__repr__
    # includes the DSN, which carries the password. Log only the
    # connection's identity.
    io.echo(
        f"bbsengine6.startup.125: caller conn id="
        f"{id(caller_conn) if caller_conn is not None else None}",
        level="debug",
    )
    io.echo(
        f"bbsengine6.startup.126: caller pool id="
        f"{id(caller_pool) if caller_pool is not None else None}",
        level="debug",
    )

    util.heading("bbsengine6 startup")

    # --- Pre-flight: admin pool against 'postgres' ---
    #
    # Always run this. The 'postgres' database is present in every
    # PostgreSQL cluster; building a pool against it gives us a working
    # connection that stage_zero can use to create args.databasename
    # if it does not yet exist. This is what makes bbsengine6.startup
    # self-heal on a fresh host where `python -m zoid6.main` (or any
    # other entry point) has never been bootstrapped before.
    io.echo(
        f"bbsengine6.startup.115: pre-flight: building admin pool "
        f"against {_ADMIN_DATABASE!r} to bootstrap target db "
        f"{args.databasename!r}",
        level="debug",
    )
    try:
        admin_pool = database.getpool(args, dbname=_ADMIN_DATABASE)
    except (ConnectionError, TimeoutError, OSError, psycopg.OperationalError) as e:
        # The admin pool is unavailable. This is the legitimate
        # "caller cannot connect to PostgreSQL at all" case; we
        # cannot bootstrap. Surface the legacy 'pool is None' error
        # so existing tooling (bed.startup.ensure_startup, casino,
        # etc.) keeps recognizing it.
        io.echo(
            f"bbsengine6.startup.100: pool is None ({e})",
            level="error",
        )
        return False

    # --- stage_zero: bootstrap (create DB, roles, schema) ---
    #
    # Forward the pre-flight admin_pool so stage_zero.access() can call
    # lib.issysop(pool=...) and verify the connecting role is a sysop
    # or superuser before stage_zero.main() runs DDL. Without this
    # kwarg, stage_zero.access() falls into the "no conn or pool"
    # branch of lib.issysop() and the whole startup aborts with
    # "check of modulename='stage_zero' failed".
    #
    # stage_zero.main() rebuilds the same pool from the
    # bbsengine6.database pool cache (database.getpool(args,
    # dbname="postgres") returns the cached admin_pool), so no extra
    # pool is opened.
    if _runstage(args, "stage_zero", pool=admin_pool, **stage_kwargs) is not True:
        io.echo(
            "bbsengine6 startup failed at stage_zero",
            level="error",
        )
        return False

    # --- stage_one: schema / data load against the target DB ---
    #
    # After stage_zero the target DB exists (or already existed).
    # Pick the right pool for stage_one:
    #   - caller_pool sanity-checked -> reuse it
    #   - else build a fresh target pool
    try:
        target_pool = _select_stage_one_pool(
            args,
            caller_pool,
            lambda: database.getpool(args, dbname=args.databasename),
        )
    except (ConnectionError, TimeoutError, OSError, psycopg.OperationalError) as e:
        io.echo(
            f"bbsengine6.startup.107: cannot build target pool ({e})",
            level="error",
        )
        return False

    try:
        with database.connect(args, pool=target_pool) as conn:
            if _runstage(args, "stage_one", conn=conn, **stage_kwargs) is not True:
                io.echo(
                    "bbsengine6 startup failed at stage_one",
                    level="error",
                )
                conn.rollback()
                return False
            conn.commit()
    except Exception:
        # database.connect or stage_one raised something we didn't
        # catch above (e.g. an unexpected SQL error inside stage_one
        # after the runmodule returned True). Surface it; the rollback
        # is implicit because the with-block exits.
        io.echo_traceback("bbsengine6.startup.main: stage_one raised:")
        return False

    io.echo("bbsengine6 startup complete", level="ok")

    # --- project-module startup: postoffice ---
    # Mirrors how casino chains into its own schema setup via the
    # bbsengine6 module runner: invoke postoffice.startup.main through
    # the same runmodule path that bin/postoffice uses. postoffice's
    # __init__.init delegates to postoffice.startup.startup_main,
    # identical in shape to casino's __init__.init delegating to
    # casino.startup.checkcasino.
    #
    # Tolerate absence so bbsengine6.startup remains runnable in
    # environments where mistermcfeely/postoffice is not installed
    # (e.g., a CI matrix that only tests bbsengine6).
    try:
        if lib.runmodule(args, "startup", package="postoffice") is False:
            io.echo("postoffice startup failed", level="error")
            return False
    except Exception:
        io.echo_traceback("bbsengine6.startup.main.postoffice_chain:")

    _maybe_subscribe_to_bed(args)
    return True
