from bbsengine6 import io, database, module, screen, util


def buildargs(args, **kwargs):
    return None


# @since 20230523
def runmodule(args, submodule, **kwargs):
    return module.runmodule(args, f"bbsengine6.backend.{submodule}", **kwargs)


# @since 20230523 copied from teos
def setbottombar(args, left, **kwargs):
    def right():
        help = " | F1: Help" if "help" in kwargs and kwargs["help"] is True else ""
        debug = " | debug" if args.debug is True else ""
        return f"con{debug}{help}"

    screen.setbottombar(left, right, **kwargs)
    return


def checkroles(args, **kwargs):
    return runmodule(args, "checkroles", **kwargs)


def checkextensions(args, **kwargs):
    return runmodule(args, "checkextensions", **kwargs)


def checkdatabase(args, **kwargs):
    return runmodule(args, "checkdatabase", **kwargs)


def checkcreatedb(args, **kwargs):
    return runmodule(args, "checkcreatedb", **kwargs)


def checksuperuser(args, **kwargs):
    return runmodule(args, "checksuperuser", **kwargs)


def createdatabase(args, **kwargs):
    return runmodule(args, "createdatabase", **kwargs)


def checkfunctions(args, **kwargs):
    return runmodule(args, "checkfunctions", **kwargs)


def checkmemberflag(args, **kwargs):
    return runmodule(args, "checkmemberflag", **kwargs)


def checkmessage(args, **kwargs):
    return runmodule(args, "checkmessage", **kwargs)


def checkwebserverrole(args, **kwargs):
    return runmodule(args, "checkwebserverrole", **kwargs)


def checkbank(args, **kwargs):
    return runmodule(args, "checkbank", **kwargs)


def checkclasses(args, **kwargs):
    return runmodule(args, "checkclasses", **kwargs)


def ok():
    io.echo(  f"{{level.ok}}  ok  {{/all}}")
    return


def fail():
    io.echo(f"{{level.fail}} fail {{/all}}")


def created():
    io.echo(  f"{{level.ok}} created {{/all}}")

# Historical note (2026-07-06): commit 8a5d1c0 removed {level.fail} and the
# level="fail" example from io/specs/echo_commands.spec on the assumption
# that no caller used them. backend.lib.fail() above emits {{level.fail}}
# fail {{/all}} and is called by checkdatabase, checkroles, checkwebserverrole,
# checkmemberflag, checksuperuser, and checkbank. Commit 7115e77 restored both lines
# in the spec. If you ever consider removing {level.fail} again, also remove
# backend.lib.fail() and migrate those callers to io.echo(level="error")
# first; otherwise the spec will be out of sync with the live API.
util.logentry(
    "backend.lib: {level.fail} is in use by fail(); spec lists it",
    module="backend.lib",
    action="level_fail_in_use",
)


def hr(failcount: int = 0) -> None:
    color = "{boxcolor}" if failcount == 0 else "{/all}{red}"
    util.hr(color=color)


# @since 20260706
def retry_on_transient(
    fn,
    *,
    attempts: int = 3,
    backoff_seconds: float = 0.1,
    retry_on: tuple = (
        "psycopg.errors.LockNotAvailable",
        "psycopg.errors.DeadlockDetected",
    ),
):
    """Run ``fn`` with bounded retry on transient DB errors.

    The DDL import path runs in a savepoint, so a transient failure
    (lock timeout, deadlock) rolls back the savepoint and the
    surrounding transaction is unaffected. We retry the failed
    ``fn`` up to ``attempts`` times with linear backoff before
    giving up. ``fn`` should not commit or release savepoints; the
    caller owns the transaction/savepoint.

    ``retry_on`` is a tuple of psycopg error class names (strings,
    not the classes themselves) to keep the import boundary clean:
    ``import psycopg`` at module load would be a layering violation
    for ``backend.lib``, so we look the classes up at call time.
    """
    import time
    import psycopg.errors as _pg_errors

    exc_classes = tuple(
        getattr(_pg_errors, name) for name in retry_on if hasattr(_pg_errors, name)
    )

    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except exc_classes as e:
            last_exc = e
            if i == attempts - 1:
                break
            time.sleep(backoff_seconds * (i + 1))
    if last_exc is not None:
        raise last_exc
    # Should not reach here if fn raises; defensive return.
    return None


# @since 20260706
def _sanitize_sp(name: str, prefix: str = "") -> str:
    base = "sp_" + prefix + "".join(ch if ch.isalnum() else "_" for ch in name)
    return base[:60]


# @since 20260707
def _ensure_autocommit_off(conn) -> None:
    """Defensively put ``conn`` into autocommit=False if it is safe to do so.

    The three savepoint-wrapped check* modules (checkclasses, checkfunctions,
    checkmessage) start their ``_work()`` with an
    ``autocommit = False`` assignment so that a caller-supplied conn in
    autocommit=True mode (e.g. from a wrapper that flipped it) still
    participates in the outer transaction. ``database.connect()`` already
    sets ``autocommit = False`` for pool-supplied conns, so the assignment
    is normally a no-op.

    psycopg forbids changing ``autocommit`` while the connection is in
    ``INTRANS`` (or ``INERROR``). The conn handed to these modules is the
    long-lived outer conn from ``stage_zero`` / ``stage_one``, which has
    already run DDL/DQL through earlier modules in the stage loop
    (``checkcreatedb``, ``checkengine``, ...). Those modules do not all
    commit or rollback at the end, so by the time ``_work()`` runs the
    conn is typically in ``INTRANS``. An unconditional
    ``conn.autocommit = False`` then raises
    ``psycopg.ProgrammingError: can't change 'autocommit' now: connection
    in transaction status INTRANS`` and aborts the whole stage.

    This helper only flips autocommit when:
      * the conn is currently in autocommit=True mode (the only case the
        defensive assignment exists to handle), AND
      * the conn is ``IDLE`` (no transaction in progress), so psycopg
        will accept the change.

    In all other cases it is a no-op. The savepoint logic that follows
    still works because psycopg treats autocommit=False as a transaction
    boundary: the next statement opens one, and the explicit
    ``conn.commit()`` / ``conn.rollback()`` at the end of ``_work()``
    closes it.
    """
    if conn.autocommit is True:
        try:
            status = conn.pgconn.transaction_status
        except Exception:
            return
        try:
            import psycopg.pq
            idle = psycopg.pq.TransactionStatus.IDLE
        except Exception:
            return
        if status == idle:
            conn.autocommit = False


# @since 20260706
def issysop(args, **kwargs) -> bool:
    """
    Check whether the current DB role has sysop privilege.

    Returns True if either:
      * current_user is a member of the 'sysop' role (pg_auth_members), OR
      * current_user has rolsuper (bootstrap fallback; the per-role
        sysop grant is handled by console, not by startup).

    Does NOT depend on engine.* tables; safe to call on a brand-new
    database that has not yet been bootstrapped.
    """
    conn = kwargs.get("conn", None)

    def _work(conn):
        with database.cursor(conn=conn) as cur:
            cur.execute(
                "SELECT 1 FROM pg_auth_members m "
                "JOIN pg_roles r ON m.roleid = r.oid "
                "WHERE r.rolname = 'sysop' "
                "  AND m.member = current_user::regrole"
            )
            if cur.rowcount > 0:
                return True
            cur.execute(
                "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
            )
            row = cur.fetchone()
            return bool(row and row["rolsuper"])

    if conn is None:
        pool = kwargs.get("pool", None)
        if pool is None:
            io.echo(
                "bbsengine6.backend.lib.issysop: no conn or pool",
                level="error",
            )
            return False
        with database.connect(args, pool=pool) as conn:
            return _work(conn)
    return _work(conn)
