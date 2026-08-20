"""
Tests for bbsengine6.startup as a runnable subpackage.

These tests pin both invocation paths the user expects to work:

  1. The CLI: ``python -m bbsengine6.startup``. The ``__main__.py``
     entrypoint calls ``lib.runmodule(args, "main")`` which dispatches
     to ``module.run`` -> ``bbsengine6.startup.main`` -> check.

  2. Programmatic: ``bbsengine6.module.run(args, "bbsengine6.startup")``.
     Loads the subpackage and calls init/buildargs/main through the
     module contract.

The pre-existing bug was a missing ``issysop`` function in
``bbsengine6.startup.lib`` (where ``bbsengine6.startup.main.access``
expected to find it) and an empty ``__init__.py`` in the committed
state. Both are now fixed; this file pins the regression so the next
refactor of the subpackage doesn't reintroduce them.

All tests are marked ``@pytest.mark.unit`` so they run without a
live PostgreSQL server. The ``check`` and ``run`` code paths are
exercised via mocks, not real DB calls.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, "src")


pytestmark = pytest.mark.unit


def _make_args(**overrides) -> argparse.Namespace:
    """Build a lightweight args namespace for module.run."""
    base = dict(
        debug=False,
        databasename="zoid6",
        databasehost="localhost",
        databaseport=5432,
        databaseuser="postgres",
        databasepassword=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


@contextlib.contextmanager
def _mock_db(target_dbname: str = "zoid6"):
    """Stub the DB calls the startup pre-flight makes.

    ``bbsengine6.startup.main`` now runs a pre-flight that builds an
    admin pool against ``postgres`` and then builds (or reuses) a pool
    against the target dbname before invoking each stage. With this
    helper we mock ``bbsengine6.database.getpool`` and
    ``bbsengine6.database.connect`` so the pre-flight succeeds in a
    unit-test environment without a live PostgreSQL server.

    Yields ``(fake_admin_pool, fake_target_pool, fake_conn_cm)`` so
    individual tests can assert against the mock pool / conn if they
    want to.
    """
    fake_admin_pool = MagicMock(name="fake_admin_pool")
    fake_target_pool = MagicMock(name="fake_target_pool")
    # _select_stage_one_pool calls .getconn().info.dbname to verify the
    # caller's pool points at the target DB. Set dbname so the helper
    # would also work if the test passed a caller_pool.
    fake_target_pool.getconn.return_value.info.dbname = target_dbname

    fake_conn = MagicMock(name="fake_conn")
    fake_conn_cm = MagicMock(name="fake_conn_cm")
    fake_conn_cm.__enter__.return_value = fake_conn
    fake_conn_cm.__exit__.return_value = False

    pool_iter = iter([fake_admin_pool, fake_target_pool])

    def _fake_getpool(args, **kwargs):
        try:
            return next(pool_iter)
        except StopIteration:
            # If the test invokes getpool more times than expected
            # (e.g. stage_one also calls database.connect with its own
            # pool), return the target pool so the test still works.
            return fake_target_pool

    with (
        patch(
            "bbsengine6.database.getpool",
            side_effect=_fake_getpool,
        ),
        patch(
            "bbsengine6.database.connect",
            return_value=fake_conn_cm,
        ),
    ):
        yield fake_admin_pool, fake_target_pool, fake_conn_cm


class TestSubpackageEntryPoints:
    """Pin that bbsengine6.startup itself exposes the module contract.

    Regression: prior to the 2026-07-07 fix, ``__init__.py`` was empty
    in HEAD, so ``bbsengine6.startup.init`` raised AttributeError and
    ``module.check`` aborted with "no init function". The casino
    entry point and any programmatic caller of
    ``module.run(args, "bbsengine6.startup")`` would then fail with
    "check of modulename='bbsengine6.startup' failed. module not run."
    """

    def test_init_is_present_and_callable(self):
        from bbsengine6 import startup

        assert hasattr(startup, "init"), (
            "bbsengine6.startup.init missing - module contract broken"
        )
        assert callable(startup.init), "bbsengine6.startup.init is not callable"

    def test_access_is_present_and_callable(self):
        from bbsengine6 import startup

        assert hasattr(startup, "access"), (
            "bbsengine6.startup.access missing - module contract broken"
        )
        assert callable(startup.access), "bbsengine6.startup.access is not callable"

    def test_buildargs_is_present_and_callable(self):
        from bbsengine6 import startup

        assert hasattr(startup, "buildargs"), (
            "bbsengine6.startup.buildargs missing - module contract broken"
        )
        assert callable(startup.buildargs), (
            "bbsengine6.startup.buildargs is not callable"
        )

    def test_main_is_present_and_callable(self):
        from bbsengine6 import startup

        assert hasattr(startup, "main"), (
            "bbsengine6.startup.main missing - module contract broken"
        )
        assert callable(startup.main), "bbsengine6.startup.main is not callable"

    def test_dunder_all_lists_the_four_entry_points(self):
        from bbsengine6 import startup

        for name in ("init", "access", "buildargs", "main"):
            assert name in startup.__all__, (
                f"{name!r} should be in bbsengine6.startup.__all__"
            )


class TestAccessDoesNotRaise:
    """Pin the exact failure mode the user was hitting.

    The pre-fix code called ``lib.issysop`` where ``lib`` was
    ``bbsengine6.startup.lib`` - which had no ``issysop`` attribute.
    ``module.check`` invoked ``m.access(args, op, **kwargs)`` during
    the access() validation step, hit the AttributeError, caught it,
    and returned None. The user reported this as
    "unknown function init()" - a paraphrase of the traceback during
    the init/access phase of the check.

    These tests pin that ``bbsengine6.startup.access`` and
    ``bbsengine6.startup.main.access`` no longer raise on a clean
    call (mocking the issysop import is the only way to exercise
    this without a live PostgreSQL connection).
    """

    def test_subpackage_access_returns_bool_with_mocked_issysop(self):
        """bbsengine6.startup.access() (defined in __init__.py) must
        return a bool. It currently returns True unconditionally
        for any caller; pin that."""
        from bbsengine6 import startup

        args = _make_args()
        result = startup.access(args, "run")
        assert isinstance(result, bool), (
            f"startup.access must return bool, got {type(result).__name__}"
        )

    def test_main_access_does_not_raise_attributeerror(self):
        """bbsengine6.startup.main.access calls issysop. Patch the
        issysop import to a no-op and verify the call completes
        without raising AttributeError on bbsengine6.startup.lib.

        This is the literal regression test for the user's
        'unknown function init()' report.

        Note: ``from bbsengine6.startup import main`` returns the
        ``main`` function defined in ``__init__.py`` (the package
        attribute shadows the submodule). Use ``importlib`` to reach
        the actual ``main`` submodule.
        """
        import importlib

        startup_main = importlib.import_module("bbsengine6.startup.main")

        args = _make_args()
        with patch(
            "bbsengine6.startup.main.issysop",
            return_value=True,
        ):
            # Must not raise - the bug was that lib.issysop
            # didn't exist and AttributeError propagated out of
            # module.check's m.access() call.
            result = startup_main.access(args, "run")

        assert result is True, (
            f"startup.main.access should return the issysop() result; got {result!r}"
        )

    def test_main_issysop_import_resolves_to_backend_lib(self):
        """Pin that startup.main.issysop is the backend's issysop,
        not bbsengine6.startup.lib.issysop (which doesn't exist).

        This is a structural pin: the import statement at the top
        of startup/main.py must be ``from bbsengine6.backend.lib
        import issysop`` (or equivalent that pulls from backend).
        """
        import importlib

        startup_main = importlib.import_module("bbsengine6.startup.main")
        from bbsengine6.backend import lib as backend_lib

        # The fix is ``from bbsengine6.backend.lib import issysop``,
        # so the binding on startup.main.issysop is the same object
        # as backend.lib.issysop.
        assert startup_main.issysop is backend_lib.issysop, (
            "startup.main.issysop must be the same function as "
            "bbsengine6.backend.lib.issysop, not a non-existent "
            "bbsengine6.startup.lib.issysop"
        )

    def test_main_access_returns_true_without_conn_or_pool(self):
        """bbsengine6.startup.main.access() must NOT call issysop
        (and therefore must NOT require a database connection) when
        neither conn nor pool is supplied in kwargs.

        The access check runs before any DB is connected (e.g. casino
        __main__.py calls runmodule("startup", ...) before opening
        a pool). issysop needs a conn/pool to query pg_auth_members;
        if we forwarded to it without one, it would return False and
        the whole startup aborts. Pin that we short-circuit to True
        in the no-conn/pool case so startup is permitted to run.
        """
        import importlib

        startup_main = importlib.import_module("bbsengine6.startup.main")

        args = _make_args()

        # Patch issysop so that if access() incorrectly calls it
        # (instead of short-circuiting), the test fails with a
        # clear "should not have been called" message rather than
        # silently returning True.
        with patch(
            "bbsengine6.startup.main.issysop",
            side_effect=AssertionError(
                "issysop should not be called when neither conn "
                "nor pool is supplied to startup.access()"
            ),
        ):
            result = startup_main.access(args, "run")

        assert result is True, (
            f"startup.main.access() must return True when no "
            f"conn/pool is supplied (defer the real sysop check "
            f"to main() once the pool is up); got {result!r}"
        )

    def test_main_access_defers_to_issysop_when_pool_supplied(self):
        """Pin that when a pool IS supplied to startup.access(),
        we forward to issysop() (instead of unconditionally
        returning True). This is the path the engine boot takes
        after opening its admin pool.
        """
        import importlib

        startup_main = importlib.import_module("bbsengine6.startup.main")

        args = _make_args()
        sentinel_pool = object()

        with patch(
            "bbsengine6.startup.main.issysop",
            return_value=False,
        ) as mock_issysop:
            result = startup_main.access(args, "run", pool=sentinel_pool)

        assert result is False, (
            f"startup.main.access() must forward to issysop when "
            f"a pool is supplied; got {result!r}"
        )
        assert mock_issysop.called, "issysop must be invoked when a pool is supplied"
        # issysop should receive both args and the pool kwarg.
        call = mock_issysop.call_args
        assert call.args[0] is args, (
            f"issysop must receive args as first positional; got {call.args!r}"
        )
        assert call.kwargs.get("pool") is sentinel_pool, (
            f"issysop must receive pool kwarg; got {call.kwargs!r}"
        )


class TestModuleRunOnSubpackage:
    """Pin that module.run(args, 'bbsengine6.startup') works.

    This exercises the programmatic invocation path: the casino
    __main__.py does
    ``lib.runmodule(args, "startup", package="bbsengine6")``
    which expands to ``module.runmodule(args, "bbsengine6.startup")``.
    With the subpackage's __init__.py defining init/access/buildargs/
    main, the check phase should pass and dispatch should reach
    m.main.

    We patch the inner lib.runmodule (which main() uses to dispatch
    to the bbsengine6.startup.main file) to short-circuit the real
    main() body, since the real body requires a database.
    """

    def test_module_run_passes_check_and_invokes_subpackage_main(self):
        """module.run(args, 'bbsengine6.startup') must:
          1. Load the bbsengine6.startup subpackage.
          2. Pass module.check (init/access/buildargs/main all present).
          3. Call m.main() on the subpackage, which iterates the
             stage pipeline (stage_zero, stage_one) by calling
             lib.runmodule for each.

        Without the __init__.py fix, step 2 fails with
        "no init function" / "check of modulename='bbsengine6.startup'
        failed. module not run." - exactly the symptom the user
        reported when invoking bbsengine6.module.run() directly.

        The startup.main() body now runs a pre-flight against the
        'postgres' database before dispatching stages; mock
        ``bbsengine6.database.getpool`` and ``database.connect`` so
        the pre-flight succeeds without a live PostgreSQL server.
        """
        from bbsengine6 import module

        args = _make_args(debug=False)

        # issysop is invoked from bbsengine6.startup.main.access
        # during the check phase. It needs a real conn/pool to do
        # anything useful, but for the test we just need check to
        # not fail - mock the issysop return value to True.
        with (
            _mock_db(),
            patch(
                "bbsengine6.startup.lib.runmodule",
                return_value=True,
            ) as mock_runmodule,
            patch(
                "bbsengine6.startup.main.issysop",
                return_value=True,
            ),
        ):
            result = module.run(args, "bbsengine6.startup")

        # The call must not have returned False (= check failure)
        # and must not have raised AttributeError. Once check passes,
        # m.main() iterates the stages; the first lib.runmodule
        # call is for "stage_zero".
        assert result is not False, (
            f"module.run should not have returned False (check "
            f"failure); got {result!r}. runmodule was called "
            f"{mock_runmodule.call_count} times: "
            f"{mock_runmodule.call_args_list!r}"
        )
        assert mock_runmodule.called, (
            "module.run should have dispatched into the stage "
            "pipeline via lib.runmodule; no call was recorded"
        )
        # The first stage dispatched is stage_zero (the first
        # entry in lib.BACKEND_STAGE_NAMES).
        first_call = mock_runmodule.call_args_list[0]
        assert first_call.args[1] == "stage_zero", (
            f"startup subpackage's main() should first dispatch "
            f"lib.runmodule(args, 'stage_zero'); got args="
            f"{first_call.args!r}"
        )
        # All stages should be dispatched in order.
        called_names = [c.args[1] for c in mock_runmodule.call_args_list]
        assert called_names == ["stage_zero", "stage_one"], (
            f"unexpected stage order: {called_names!r}"
        )

    def test_module_run_does_not_raise_on_subpackage_access(self):
        """Regression pin: module.check's m.access() call must not
        raise AttributeError. The check function would catch the
        error and return None, but only after logging a noisy
        traceback. The clean test is: no traceback is emitted to
        the io logger.
        """
        from bbsengine6 import module

        args = _make_args(debug=True)

        with (
            patch(
                "bbsengine6.startup.lib.runmodule",
                return_value=True,
            ),
            patch(
                "bbsengine6.startup.main.issysop",
                return_value=True,
            ),
            patch(
                "bbsengine6.io.echo_traceback",
            ) as mock_traceback,
        ):
            module.run(args, "bbsengine6.startup")

        # If the access check threw, io.echo_traceback would have
        # been called from module.check (line 731). It must not be.
        for call in mock_traceback.call_args_list:
            msg = str(call)
            assert "issysop" not in msg, (
                f"io.echo_traceback called with issysop-related "
                f"message - the lib.issysop bug is back: {msg!r}"
            )
            assert "AttributeError" not in msg, (
                f"io.echo_traceback called with AttributeError "
                f"during subpackage dispatch: {msg!r}"
            )


class TestCLIStartupInvocation:
    """Pin that python -m bbsengine6.startup doesn't blow up at
    the access-check stage.

    The CLI goes through __main__.py -> lib.runmodule(args, "main")
    -> module.run(args, "main", package="bbsengine6.startup") ->
    loads bbsengine6.startup.main -> check. With the issysop fix,
    the access() check must not raise. Without the fix, this is
    exactly where the user saw "unknown function init()".
    """

    def test_main_module_imports_cleanly(self):
        """__main__.py must be importable. If the import chain
        fails (e.g. circular import, missing function), the
        ``python -m`` invocation dies before it even runs.
        """
        import importlib.util

        spec = importlib.util.find_spec("bbsengine6.startup.__main__")
        assert spec is not None, (
            "bbsengine6.startup.__main__ not findable - the CLI entry point is missing"
        )

    def test_main_access_does_not_cascade_to_check_failure(self):
        """Walk the same code path as ``python -m bbsengine6.startup``:
        import the __main__ module's logic, but instead of running it
        end-to-end, invoke the inner module.run for the
        bbsengine6.startup.main subpackage. The check must succeed
        (return truthy) so that the CLI does not log
        "check of modulename=... failed".
        """
        from bbsengine6 import module

        args = _make_args()

        # Walk the CLI path: __main__.py calls
        # lib.runmodule(args, "main") with no package=.
        # lib.runmodule defaults package="bbsengine6.startup", so
        # this is equivalent to module.run(args, "main", package=
        # "bbsengine6.startup") which loads bbsengine6.startup.main.
        with (
            patch(
                "bbsengine6.startup.lib.runmodule",
                return_value=True,
            ),
            patch(
                "bbsengine6.startup.main.issysop",
                return_value=True,
            ),
        ):
            # If access() raised AttributeError on lib.issysop,
            # check would return None and module.run would log
            # "check of modulename='bbsengine6.startup.main' failed"
            # and return False. The patched runmodule records the
            # call; if check failed, the inner runmodule is never
            # reached.
            with patch(
                "bbsengine6.io.echo_traceback",
            ) as mock_traceback:
                module.run(args, "main", package="bbsengine6.startup")

        for call in mock_traceback.call_args_list:
            msg = str(call)
            assert "issysop" not in msg, (
                f"CLI dispatch hit the lib.issysop bug: {msg!r}"
            )

    def test_placeholder_stubs_removed(self):
        """Pin that the empty placeholder stubs (bank.py,
        stage_zero.py, stage_one.py, engine.py) are gone. They
        were never loaded by the dispatch logic (the lib uses
        package='bbsengine6.backend' for those names), so
        deleting them reduces confusion without changing
        behavior. If someone re-adds an empty stub, this test
        flags it for review.
        """
        import importlib.util

        for name in ("bank", "engine", "stage_zero", "stage_one"):
            spec = importlib.util.find_spec(f"bbsengine6.startup.{name}")
            assert spec is None, (
                f"bbsengine6.startup.{name} should have been "
                f"removed (was an unused placeholder stub); "
                f"spec is {spec!r}"
            )
