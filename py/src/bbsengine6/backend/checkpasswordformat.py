"""
Install ``chk_member_password_bcrypt`` on ``engine.__member`` and audit
the column for any legacy ``$1$`` MD5-crypt hashes.

Wired into ``backend.stage_one`` immediately after ``checkclasses`` so
the engine schema and its member table are already in place when the
constraint lands. Runs on every ``bbsengine6.startup`` invocation, so
operators no longer need to ``psql \\i bbsengine6.sql`` manually to get
the hardening applied.

Two phases, both SAVEPOINT-protected so a transient failure rolls back
cleanly without aborting the outer stage transaction:

  1. Idempotent constraint install. ``database.constraintexists`` is
     the cheap probe; if False, ``manage_password_format.sql`` is
     loaded via ``database.importsql`` inside a savepoint. The SQL
     itself is also idempotent (``alter table ... drop constraint if
     exists`` then ``add constraint``), so re-running the file is safe
     even if the probe is bypassed.

  2. Audit. ``bbsengine6.member.audit_password_column`` is called
     unconditionally on the same connection. Any monikers holding a
     ``$1$`` hash are logged at ``level="warning"``; the operator sees
     a one-line diagnostic per row instead of a silent checkpassword
     failure.

Dependency order:

  * ``checkengine`` (already ran in stage_one — engine schema exists
    and is owned by zoid6).
  * ``checkclasses`` (already ran — engine.__member table exists).

The constraint install respects both preconditions via the stage_one
module ordering; this module does not duplicate the schema/table
creation.
"""

from bbsengine6 import io, database
from bbsengine6.database import constraintexists
from bbsengine6.member import lib as memberlib

from bbsengine6.backend import lib


CONSTRAINT_NAME = "chk_member_password_bcrypt"
CONSTRAINT_SCHEMA = "engine"
CONSTRAINT_TABLE = "engine.__member"
CONSTRAINT_SQL_FILE = "manage_password_format.sql"


def init(args, **kwargs) -> bool:
    return True


def buildargs(args, **kwargs):
    return lib.buildargs(args, **kwargs)


def access(args, op, **kwargs) -> bool:
    return lib.issysop(args, **kwargs)


def main(args, **kwargs) -> bool:
    def _work(conn):
        lib._ensure_autocommit_off(conn)
        failcount = 0

        # --- 1. constraint install (idempotent) ---
        io.echo(
            f"{{var:labelcolor}}constraint {{var:valuecolor}}{CONSTRAINT_NAME}"
            f"{{var:labelcolor}}: ",
            end="",
        )
        if constraintexists(
            args,
            CONSTRAINT_SCHEMA,
            CONSTRAINT_NAME,
            conn=conn,
        ) is True:
            io.echo("ok", level="ok")
        else:
            io.echo("import ", end="")
            sp = lib._sanitize_sp(CONSTRAINT_NAME, prefix="ck_")
            with database.cursor(conn=conn) as cur:
                cur.execute(f"SAVEPOINT {sp}")
            try:
                ok = lib.retry_on_transient(
                    lambda: database.importsql(
                        args, CONSTRAINT_SQL_FILE, conn=conn, rollback=False
                    )
                )
            except Exception as e:
                io.echo_traceback(
                    f"checkpasswordformat: retry exhausted for "
                    f"{CONSTRAINT_NAME}: {e}"
                )
                ok = False
            if ok is False:
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"ROLLBACK TO SAVEPOINT {sp}")
                io.echo("fail", level="error")
                failcount += 1
            else:
                with database.cursor(conn=conn) as cur:
                    cur.execute(f"RELEASE SAVEPOINT {sp}")
                io.echo("ok", level="ok")

        # --- 2. audit (unconditional) ---
        # Audit runs even if the install failed: the operator still
        # wants to know how many legacy $1$ rows are present, because
        # that count is the migration signal regardless of whether
        # the constraint landed. member.audit_password_column logs
        # each legacy row at level="warning" and returns the list.
        try:
            legacy = memberlib.audit_password_column(args, conn=conn)
        except Exception as e:
            io.echo_traceback(
                f"checkpasswordformat: audit_password_column raised: {e}"
            )
            legacy = None

        if legacy is None:
            io.echo(
                "audit_password_column: pool/conn missing or query failed",
                level="error",
            )
            failcount += 1
        elif len(legacy) == 0:
            io.echo(
                f"audit_password_column: 0 row(s) with $1$ hash in "
                f"{CONSTRAINT_TABLE}",
                level="ok",
            )
        else:
            io.echo(
                f"audit_password_column: {len(legacy)} row(s) with $1$ "
                f"hash in {CONSTRAINT_TABLE}: {','.join(legacy)}",
                level="warning",
            )

        if failcount == 0:
            conn.commit()
        else:
            conn.rollback()
        return True if failcount == 0 else False

    conn = kwargs.get("conn", None)
    return _work(conn)
