# tests/test_startup_postoffice_chain.py
# Tests that bbsengine6.startup.main chains into postoffice.startup.main
# after stage_one succeeds, mirroring how casino chains into its own
# schema setup via the bbsengine6 module runner.

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest


def _make_args(dbname: str):
    args = MagicMock(name="args")
    args.databasename = dbname
    args.verbose = False
    args.debug = False
    args.pool = None
    args.conn = None
    return args


def _make_fake_conn():
    conn = MagicMock(name="conn")
    conn.rollback = MagicMock()
    conn.commit = MagicMock()
    return conn


class _Harness:
    """Wires up the standard mocks for a startup.main test.

    Records runmodule calls so tests can assert ordering and kwargs.
    """

    def __init__(self, *, runmodule_returns=True, runmodule_per_submodule=None):
        self.runmodule_returns = runmodule_returns
        self.runmodule_per_submodule = runmodule_per_submodule or {}
        self.run_calls = []
        self.args = _make_args("zoid6_test_postoffice_chain")

    def __enter__(self):
        def fake_runmodule(args, submodule, **kwargs):
            self.run_calls.append((submodule, dict(kwargs)))
            if submodule in self.runmodule_per_submodule:
                return self.runmodule_per_submodule[submodule]
            return self.runmodule_returns

        self._patches = [
            patch("bbsengine6.startup.lib.runmodule", side_effect=fake_runmodule),
            patch("bbsengine6.database.getpool", return_value=MagicMock(name="pool")),
        ]
        fake_conn = _make_fake_conn()
        fake_cm = MagicMock(name="connect_cm")
        fake_cm.__enter__ = MagicMock(return_value=fake_conn)
        fake_cm.__exit__ = MagicMock(return_value=False)
        self._patches.append(
            patch("bbsengine6.database.connect", return_value=fake_cm)
        )
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        for p in reversed(self._patches):
            p.stop()


@pytest.mark.unit
class TestStartupChainsIntoPostoffice:
    """bbsengine6.startup.main must call runmodule(args, "startup",
    package="postoffice") after stage_one succeeds.

    Mirrors the casino pattern: casino's __main__ calls runmodule(args,
    "startup", package="bbsengine6") which invokes bbsengine6.startup.main
    to land the engine schema; casino's own schema setup is invoked
    directly via bin/casino --direct (casino.startup.main), not chained
    from bbsengine6. Here we test the analogous chain for postoffice.
    """

    def test_postoffice_chain_runs_after_stage_one(self):
        """startup.main() invokes runmodule with package='postoffice'
        for the 'startup' submodule, after stage_zero and stage_one."""
        with _Harness() as h:
            startup_main = importlib.import_module(
                "bbsengine6.startup.main"
            ).main

            result = startup_main(h.args, conn=None, pool=None)

        assert result is True
        submodules_called = [name for name, _ in h.run_calls]
        assert "stage_zero" in submodules_called
        assert "stage_one" in submodules_called
        # The postoffice chain: must call runmodule(args, "startup",
        # package="postoffice").
        postoffice_calls = [
            (name, kw) for name, kw in h.run_calls if kw.get("package") == "postoffice"
        ]
        assert len(postoffice_calls) == 1, (
            f"expected exactly one postoffice chain call, got {postoffice_calls!r}"
        )
        name, _ = postoffice_calls[0]
        assert name == "startup"
        # The postoffice chain runs AFTER stage_one.
        idx_stage_one = submodules_called.index("stage_one")
        idx_postoffice = submodules_called.index(name)
        assert idx_postoffice > idx_stage_one, (
            "postoffice chain must run after stage_one"
        )

    def test_postoffice_chain_failure_aborts_startup(self):
        """If the postoffice chain returns False, startup.main returns
        False (and does NOT proceed to bed subscription)."""
        with _Harness() as h:
            captured_calls = []

            def selective_fake(args, submodule, **kwargs):
                captured_calls.append((submodule, kwargs))
                return kwargs.get("package") != "postoffice"

            with patch(
                "bbsengine6.startup.lib.runmodule", side_effect=selective_fake
            ):
                startup_main = importlib.import_module(
                    "bbsengine6.startup.main"
                ).main
                result = startup_main(h.args, conn=None, pool=None)

        assert result is False
        # Confirm the postoffice chain was actually attempted.
        postoffice_calls = [
            c for c in captured_calls if c[1].get("package") == "postoffice"
        ]
        assert len(postoffice_calls) == 1

    def test_postoffice_chain_tolerates_import_error(self):
        """If postoffice is not importable, startup.main swallows the
        error and returns True (so bbsengine6 startup remains runnable
        in environments without mistermcfeely/postoffice installed)."""
        with _Harness() as h:
            startup_main = importlib.import_module(
                "bbsengine6.startup.main"
            ).main

            # Patch runmodule to raise ImportError only when the
            # postoffice chain is invoked; everything else succeeds.
            def selective_fake(args, submodule, **kwargs):
                if kwargs.get("package") == "postoffice":
                    raise ImportError("simulated: postoffice not installed")
                return True

            with patch(
                "bbsengine6.startup.lib.runmodule", side_effect=selective_fake
            ):
                result = startup_main(h.args, conn=None, pool=None)

        # Tolerated -- startup continues.
        assert result is True

    def test_postoffice_chain_tolerates_generic_exception(self):
        """Generic exceptions during the postoffice chain are also
        tolerated (logged via echo_traceback, startup continues)."""
        with _Harness() as h:
            startup_main = importlib.import_module(
                "bbsengine6.startup.main"
            ).main

            def selective_fake(args, submodule, **kwargs):
                if kwargs.get("package") == "postoffice":
                    raise RuntimeError("simulated failure")
                return True

            with patch(
                "bbsengine6.startup.lib.runmodule", side_effect=selective_fake
            ):
                result = startup_main(h.args, conn=None, pool=None)

        assert result is True
