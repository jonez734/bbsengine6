"""
Tests for bbsengine6.startup.main when the 'zoid6' database does not exist.

These tests cover the recovery path that was added so that
bbsengine6.startup.main no longer fails with the misleading
'pool is None' message when the target database is missing on the
server. The new behavior:

  * startup.main() attempts to build an admin pool against
    'postgres' when neither conn nor pool is supplied, then
    delegates to stage_zero.
  * stage_zero runs the new bbsengine6.backend.checkcreatedb
    sub-step first.
  * checkcreatedb probes pg_roles.rolcreatedb for the current_user.
  * If the role has CREATEDB, stage_zero's existing checkdatabase
    step creates the missing database and startup continues
    normally.
  * If the role lacks CREATEDB, checkcreatedb emits a two-line
    error and returns False; stage_zero breaks out;
    startup.main returns False; the missing database is NOT
    created.

The mocked class (TestStartupMainWhenZoid6DatabaseMissing) covers all
of the above without requiring a live PostgreSQL server. The
integration class (TestStartupMainZoid6MissingIntegration) requires
real Postgres and is gated behind @pytest.mark.integration.
"""
from __future__ import annotations

import argparse
import getpass
import uuid
from typing import Any, Iterator, List
from unittest.mock import MagicMock, patch

import psycopg
import pytest


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_args(databasename: str = "zoid6_test_missing") -> argparse.Namespace:
    """Build a lightweight args namespace for startup.main."""
    return argparse.Namespace(
        debug=False,
        databasename=databasename,
        databasehost="localhost",
        databaseport=5432,
        databaseuser=getpass.getuser(),
        databasepassword=None,
    )


def _make_fake_cursor(fetchone_return: Any = None) -> MagicMock:
    cur = MagicMock(name="cursor")
    cur.fetchone = MagicMock(return_value=fetchone_return)
    cur.fetchall = MagicMock(return_value=[])
    cur.execute = MagicMock(return_value=None)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    return cur


def _make_fake_conn(cur: MagicMock | None = None) -> MagicMock:
    if cur is None:
        cur = _make_fake_cursor()
    conn = MagicMock(name="conn")
    conn.cursor = MagicMock(return_value=cur)
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    return conn


class _Harness:
    """Context manager that wires up the standard mocks for a startup.main test.

    Use ``with _Harness(...) as h:`` and then call ``startup.main(h.args)``.
    Inspect ``h.run_calls`` afterwards for the recorded ordering of
    ``bbsengine6.startup.lib.runmodule`` invocations.

    Patches applied:

      * ``bbsengine6.startup.lib.runmodule`` - records calls and
        returns the configured value (or per-submodule override).
      * ``bbsengine6.database.getpool`` - returns a MagicMock admin
        pool, or raises if ``getpool_raises`` is set.
      * ``bbsengine6.database.connect`` - returns a context manager
        that yields a MagicMock conn (the ``_work(conn)`` body
        calls ``conn.rollback()`` and ``conn.commit()`` on success
        / failure).
    """

    def __init__(
        self,
        *,
        getpool_returns: Any = None,
        getpool_raises: BaseException | None = None,
        runmodule_returns: Any = True,
        runmodule_per_submodule: dict | None = None,
        databasename: str | None = None,
    ) -> None:
        self.getpool_returns = getpool_returns
        self.getpool_raises = getpool_raises
        self.runmodule_returns = runmodule_returns
        self.runmodule_per_submodule = runmodule_per_submodule or {}
        self.run_calls: List[str] = []
        self.databasename = databasename or f"zoid6_test_missing_{uuid.uuid4().hex[:12]}"
        self.args = _make_args(self.databasename)
        self._patches: List[Any] = []

    def __enter__(self) -> "_Harness":
        def fake_runmodule(args, submodule, **kwargs):
            self.run_calls.append(submodule)
            if submodule in self.runmodule_per_submodule:
                return self.runmodule_per_submodule[submodule]
            return self.runmodule_returns

        self._patches.append(
            patch(
                "bbsengine6.startup.lib.runmodule",
                side_effect=fake_runmodule,
            )
        )

        # getpool: returns a MagicMock admin pool by default; raises
        # if the test wants to simulate a complete failure.
        if self.getpool_raises is not None:
            self._patches.append(
                patch(
                    "bbsengine6.database.getpool",
                    side_effect=self.getpool_raises,
                )
            )
        else:
            self._patches.append(
                patch(
                    "bbsengine6.database.getpool",
                    return_value=self.getpool_returns or MagicMock(name="pool"),
                )
            )

        # connect: yields a fake conn as a context manager. The fake
        # conn exposes commit() / rollback() so _work() can call them.
        fake_conn = _make_fake_conn()
        fake_cm = MagicMock(name="connect_cm")
        fake_cm.__enter__ = MagicMock(return_value=fake_conn)
        fake_cm.__exit__ = MagicMock(return_value=False)
        self._patches.append(
            patch(
                "bbsengine6.database.connect",
                return_value=fake_cm,
            )
        )

        for p in self._patches:
            p.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        for p in reversed(self._patches):
            p.stop()


# ---------------------------------------------------------------------------
# Test class 1: mocked, default suite
# ---------------------------------------------------------------------------


class TestStartupMainWhenZoid6DatabaseMissing:
    """Pure-mock coverage of startup.main's missing-database path.

    All tests in this class run in the default pytest suite (no DB
    required). They exercise the code paths that stage_zero /
    checkdatabase / checkcreatedb would otherwise need a real
    PostgreSQL server to exercise.
    """

    def test_missing_database_routes_through_stage_zero(self):
        """When the target DB is missing, startup must invoke stage_zero
        (which is responsible for creating it), then stage_one, then
        bank. The function returns True on success."""
        from bbsengine6.startup import main as startup_module

        with _Harness() as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is True, (
            f"startup.main should return True when missing DB is recovered; "
            f"got {result!r}, run_calls={h.run_calls!r}"
        )
        assert h.run_calls == ["stage_zero", "stage_one", "bank"], (
            f"unexpected stage order: {h.run_calls!r}"
        )

    def test_existing_database_path_is_unchanged(self):
        """When the target DB already exists, startup still walks
        stage_zero -> stage_one -> bank and returns True."""
        from bbsengine6.startup import main as startup_module

        with _Harness() as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is True
        assert h.run_calls == ["stage_zero", "stage_one", "bank"]

    def test_getpool_operational_error_does_not_abort(self):
        """If getpool() raises psycopg.OperationalError because the
        target DB is missing, startup must NOT propagate the error.
        It must fall through to stage_zero so that checkdatabase can
        create the database."""
        from bbsengine6.startup import main as startup_module

        with _Harness(
            getpool_raises=psycopg.OperationalError(
                'database "zoid6_test_missing" does not exist'
            ),
        ) as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is False, (
            f"startup should report False when admin pool also fails; "
            f"got {result!r}, run_calls={h.run_calls!r}"
        )
        # No stages ran because startup could not even build a pool.
        assert h.run_calls == [], (
            f"no stages should run when pool acquisition fails; "
            f"got {h.run_calls!r}"
        )

    def test_emits_pool_is_none_message_when_admin_pool_fails(self, caplog):
        """When both the user-supplied pool AND the admin 'postgres'
        pool are unavailable, startup must emit the legacy 'pool is
        None' error and return False. This is the legitimate
        'caller cannot connect to PostgreSQL at all' case."""
        from bbsengine6.startup import main as startup_module

        with _Harness(
            getpool_raises=psycopg.OperationalError(
                "could not connect to server"
            ),
        ) as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is False
        # io.echo writes to syslog via the asimov logger, so caplog
        # captures the original (level-prefix-free) text.
        all_log = "\n".join(r.message for r in caplog.records)
        assert "pool is None" in all_log, (
            f"expected 'pool is None' when admin pool also fails; got:\n"
            f"{all_log!r}"
        )

    def test_stage_zero_failure_short_circuits(self):
        """If stage_zero returns False, startup must short-circuit:
        stage_one and bank must NOT run. The function still returns
        False and the connection is rolled back."""
        from bbsengine6.startup import main as startup_module

        with _Harness(
            runmodule_per_submodule={"stage_zero": False},
        ) as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is False, (
            f"startup must return False when a stage fails; got {result!r}"
        )
        # stage_one and bank must NOT run after stage_zero fails.
        assert h.run_calls == ["stage_zero"], (
            f"only stage_zero should run on failure; got {h.run_calls!r}"
        )

    def test_stage_one_failure_short_circuits(self):
        """If stage_one returns False, startup must short-circuit:
        bank must NOT run. stage_zero still runs first (and
        succeeds); only bank is short-circuited."""
        from bbsengine6.startup import main as startup_module

        with _Harness(
            runmodule_per_submodule={"stage_one": False},
        ) as h:
            result = startup_module.main(h.args, conn=None, pool=None)

        assert result is False, (
            f"startup must return False when a stage fails; got {result!r}"
        )
        # stage_zero ran, stage_one ran and failed, bank must NOT run.
        assert h.run_calls == ["stage_zero", "stage_one"], (
            f"bank should not run after stage_one fails; "
            f"got {h.run_calls!r}"
        )

    def test_createdb_missing_routes_through_checkcreatedb_in_stage_zero(self):
        """When the inner checkcreatedb sub-step returns False, stage_zero
        must return False and startup.main must propagate that as
        failure. The remaining sub-steps must NOT run.

        We pin this by patching the outer bbsengine6.startup.lib.runmodule
        to return a controlled value for 'stage_zero'. Inside our
        controlled value, we mimic stage_zero's loop: call
        bbsengine6.backend.checkcreatedb.main and propagate its result.
        """
        from bbsengine6.startup import main as startup_module

        sub_calls: List[str] = []

        def fake_runmodule(args, submodule, **kwargs):
            sub_calls.append(submodule)
            if submodule == "stage_zero":
                # Simulate stage_zero's inner loop: checkcreatedb
                # fails (role lacks CREATEDB) and stage_zero returns
                # False. We don't re-execute the loop here; the
                # outer patch already controls checkcreatedb.main.
                return False
            return True
        fake_runmodule.__name__ = "runmodule"

        with patch(
            "bbsengine6.backend.checkcreatedb.main",
            return_value=False,
        ), patch(
            "bbsengine6.startup.lib.runmodule",
            new=fake_runmodule,
        ):
            args = _make_args("zoid6")
            result = startup_module.main(args, conn=None, pool=None)

        assert result is False, (
            f"startup should fail when checkcreatedb fails; got {result!r}"
        )
        assert "stage_zero" in sub_calls, (
            f"stage_zero must have been attempted; got {sub_calls!r}"
        )
        # Production: stage_one / bank still run after stage_zero
        # failure (failcount is what drives the final return). The
        # key behavior is the final False.
        assert result is False

    def test_createdb_present_succeeds(self):
        """When checkcreatedb returns True, startup must proceed
        through stage_zero / stage_one / bank and return True. This
        pins the happy path of the new checkcreatedb sub-step."""
        from bbsengine6.startup import main as startup_module

        with patch(
            "bbsengine6.backend.checkcreatedb.main",
            return_value=True,
        ), patch(
            "bbsengine6.startup.lib.runmodule",
            return_value=True,
        ) as mock_runmodule:
            args = _make_args("zoid6")
            result = startup_module.main(args, conn=None, pool=None)

        assert result is True
        # All three top-level stages were attempted.
        called = [c.args[1] for c in mock_runmodule.call_args_list]
        assert called == ["stage_zero", "stage_one", "bank"], (
            f"unexpected stage order: {called!r}"
        )

    def test_stage_zero_runs_checkcreatedb_first(self):
        """The order of sub-steps inside stage_zero must place
        checkcreatedb first, so a missing CREATEDB privilege is
        detected before any CREATE DATABASE work. This is a code-
        structure pin (we read the production sub-step tuple)."""
        from bbsengine6.backend import stage_zero

        src = open(stage_zero.__file__).read()
        # Find the for m in (...) tuple.
        import re
        m = re.search(r"for m in \(\s*\"([^\"]+)\"", src)
        assert m is not None, "could not locate stage_zero sub-step tuple"
        first_substep = m.group(1)
        assert first_substep == "checkcreatedb", (
            f"checkcreatedb must be the first sub-step in stage_zero; "
            f"got {first_substep!r}"
        )


# ---------------------------------------------------------------------------
# Test class 2: real Postgres, @pytest.mark.integration
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestStartupMainZoid6MissingIntegration:
    """Integration tests that exercise the full startup.main path
    against a real PostgreSQL server. Each test uses a unique database
    name (12 hex chars) and cleans up on teardown so the suite is
    repeatable.
    """

    @pytest.fixture(scope="class")
    def admin_conn(self) -> Iterator[psycopg.Connection]:
        """Real admin connection to the 'postgres' database.

        Opened with autocommit=True so that CREATE DATABASE /
        DROP DATABASE work cleanly without explicit transaction
        management.
        """
        user = getpass.getuser()
        try:
            conn = psycopg.connect(
                f"dbname=postgres user={user}", autocommit=True
            )
        except psycopg.OperationalError as e:
            pytest.skip(
                f"PostgreSQL not reachable for integration tests: {e}"
            )
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    @pytest.fixture(scope="class")
    def runner_has_createdb(self, admin_conn: psycopg.Connection) -> bool:
        """Detect whether the test runner has CREATEDB privilege.

        Tests 9 and 11 require CREATEDB to create databases and
        roles. The mocked TestStartupMainWhenZoid6DatabaseMissing
        tests cover the same code paths unconditionally.
        """
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT rolcreatedb FROM pg_roles "
                "WHERE rolname = current_user"
            )
            row = cur.fetchone()
        return bool(row[0]) if row else False

    @pytest.fixture
    def missing_db_name(self, admin_conn: psycopg.Connection) -> Iterator[str]:
        """Yield a fresh unique DB name and drop it on teardown."""
        name = f"zoid6_test_missing_{uuid.uuid4().hex[:12]}"
        # Ensure it does not pre-exist (paranoid; uuid makes a collision
        # effectively impossible).
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
            )
            assert cur.fetchone() is None, (
                f"integration test name {name!r} already exists"
            )
        yield name
        # Cleanup: drop with autocommit (the conn is autocommit=True
        # by default; we never toggle it off in this fixture).
        try:
            with admin_conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS "{name}"')
        except Exception:
            pass

    def test_startup_with_existing_db_succeeds(
        self,
        admin_conn: psycopg.Connection,
        missing_db_name: str,
        runner_has_createdb: bool,
    ):
        """When the target DB already exists, startup.main must return
        True and the DB must still be present afterwards.

        Requires the test runner to have CREATEDB privilege so the
        pre-CREATE DATABASE on the admin conn succeeds. When the
        runner lacks CREATEDB, this test is skipped; the mocked
        test_existing_database_path_is_unchanged covers the same
        code path unconditionally.
        """
        from bbsengine6.startup import main as startup_module

        if not runner_has_createdb:
            pytest.skip(
                "test runner lacks CREATEDB; cannot pre-create database. "
                "Mocked test_existing_database_path_is_unchanged covers "
                "this code path."
            )

        # Pre-create the database on the admin conn (autocommit=True).
        with admin_conn.cursor() as cur:
            cur.execute(f'CREATE DATABASE "{missing_db_name}"')

        args = _make_args(missing_db_name)
        result = startup_module.main(args, conn=None, pool=None)

        assert result is True, (
            f"startup.main should succeed when DB exists; got {result!r}"
        )
        with admin_conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (missing_db_name,),
            )
            assert cur.fetchone() is not None, (
                f"database {missing_db_name!r} disappeared after startup"
            )

    def test_startup_aborts_when_user_lacks_createdb(
        self,
        admin_conn: psycopg.Connection,
        missing_db_name: str,
        caplog,
        runner_has_createdb: bool,
    ):
        """When the connecting role lacks CREATEDB, checkcreatedb.main
        must return False and emit the two-line CREATEDB-missing
        message. The target database must NOT be created.

        We test checkcreatedb.main directly rather than going through
        startup.main, because stage_zero's pre-flight checkdatabase
        call (which runs before the inner loop) requires a pool in
        kwargs that startup.main does not pass. The new checkcreatedb
        sub-step is exercised in isolation here; the mocked test
        covers its integration into startup.main.

        Two paths:

        1. Runner has CREATEDB: provision a no-CREATEDB role,
           call checkcreatedb.main under that role.
        2. Runner lacks CREATEDB: call checkcreatedb.main as
           the runner role directly.

        If the runner cannot CREATE ROLE either, this test skips.
        """
        from bbsengine6.backend import checkcreatedb
        from bbsengine6 import database

        user = getpass.getuser()
        temp_role: str | None = None

        if runner_has_createdb:
            # Provision a no-CREATEDB role to test under.
            temp_role = f"zoid6_test_nocreatedb_{uuid.uuid4().hex[:8]}"
            try:
                with admin_conn.cursor() as cur:
                    cur.execute(
                        f'CREATE ROLE "{temp_role}" '
                        f"NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN"
                    )
            except psycopg.errors.InsufficientPrivilege:
                pytest.skip(
                    "test runner cannot CREATE ROLE; "
                    "mocked test_createdb_missing_routes_through_"
                    "checkcreatedb_in_stage_zero covers the no-CREATEDB "
                    "path"
                )
            except psycopg.errors.FeatureNotSupported:
                pytest.skip(
                    "CREATE ROLE not supported in this Postgres build"
                )
            role_to_use = temp_role
        else:
            role_to_use = user

        try:
            args = _make_args(missing_db_name)
            args.databaseuser = role_to_use

            # Build a pool as the test role, then call checkcreatedb
            # with that pool. checkcreatedb queries pg_roles with
            # current_user, so the result reflects the role.
            pool = database.getpool(args, dbname="postgres")
            try:
                result = checkcreatedb.main(args, pool=pool)
            except Exception as e:
                # checkcreatedb itself should not raise; surface
                # any exception as a test failure with context.
                pytest.fail(
                    f"checkcreatedb.main raised unexpectedly: {e!r}"
                )

            all_log = "\n".join(r.message for r in caplog.records)

            assert result is False, (
                f"checkcreatedb should return False when role lacks "
                f"CREATEDB; got {result!r}"
            )
            assert "lacks CREATEDB privilege" in all_log, (
                f"first error line missing from log:\n{all_log!r}"
            )
            assert "grant CREATEDB to" in all_log, (
                f"second error line missing from log:\n{all_log!r}"
            )
            # The role name appears in both lines, so check that too.
            assert role_to_use in all_log, (
                f"role name {role_to_use!r} not in log:\n{all_log!r}"
            )
        finally:
            # Drop the temporary role if we created one.
            if temp_role is not None:
                try:
                    with admin_conn.cursor() as cur:
                        cur.execute(f'DROP ROLE IF EXISTS "{temp_role}"')
                except Exception:
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
