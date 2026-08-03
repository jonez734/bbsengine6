"""
Tests for the bed-subscription hook in bbsengine6.startup.

The startup subpackage's main() calls _maybe_subscribe_to_bed() at
the end of bootstrap. If bed is reachable, the current session
opens a BedMessageServiceClient subscription for the logged-in
moniker and starts receiving server-push notifications. If bed is
unreachable (no daemon, network down, etc.) the call is a no-op
and getch.py/bottombar.py fall back to direct DB reads.

NOTE: ``from bbsengine6.startup import main`` returns the *function*
``main`` (the entry point), NOT the ``main.py`` submodule — the
__init__.py does ``from .main import init, access, buildargs, main``
which shadows the submodule. These tests use
``importlib.import_module("bbsengine6.startup.main")`` to get the
real submodule.

Coverage:
  - _maybe_subscribe_to_bed() success path
  - _maybe_subscribe_to_bed() no-moniker early return
  - _maybe_subscribe_to_bed() bed-unreachable path
  - _maybe_subscribe_to_bed() import-failure traceback
  - main() actually invokes _maybe_subscribe_to_bed after a
    successful stage run
"""

from __future__ import annotations

import argparse
import importlib
from unittest.mock import MagicMock, patch

import pytest


def _make_args(**overrides) -> argparse.Namespace:
    """Build a minimal args namespace for the startup module."""
    args = argparse.Namespace(
        databasename="zoid6",
        databasehost="localhost",
        databaseuser=None,
        databaseport=5432,
        databasepassword=None,
        bed_host=None,
        bed_port=None,
    )
    for k, v in overrides.items():
        setattr(args, k, v)
    return args


def _load_startup_main():
    """Load bbsengine6.startup.main as the *module*, not the function."""
    return importlib.import_module("bbsengine6.startup.main")


# ---------------------------------------------------------------------------
# _maybe_subscribe_to_bed: success path
# ---------------------------------------------------------------------------


class TestMaybeSubscribeToBedSuccess:
    """When bed is reachable and the user is logged in, the hook
    should call subscribe_to_bed_sync and return True."""

    def test_returns_true_when_subscribe_succeeds(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock()
        fake_threadlocal.moniker = "alice"

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main, "subscribe_to_bed_sync", return_value=True
        ) as subscribe, patch(
            "bbsengine6.io.echo"
        ) as echo:
            result = startup_main._maybe_subscribe_to_bed(_make_args())

        assert result is True
        subscribe.assert_called_once()
        args_call = subscribe.call_args[0]
        assert args_call[1] == "alice"

    def test_logs_info_on_success(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock()
        fake_threadlocal.moniker = "alice"

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main, "subscribe_to_bed_sync", return_value=True
        ), patch(
            "bbsengine6.io.echo"
        ) as echo:
            startup_main._maybe_subscribe_to_bed(_make_args())

        info_calls = [
            c for c in echo.call_args_list
            if c.kwargs.get("level") == "info"
        ]
        assert len(info_calls) >= 1
        assert "alice" in info_calls[0].args[0]


# ---------------------------------------------------------------------------
# _maybe_subscribe_to_bed: no moniker (not logged in)
# ---------------------------------------------------------------------------


class TestMaybeSubscribeNoMoniker:
    """If no moniker is in threadlocal, the hook should return False
    without calling subscribe_to_bed_sync."""

    def test_returns_false_when_no_moniker(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock()
        fake_threadlocal.moniker = None

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main, "subscribe_to_bed_sync"
        ) as subscribe:
            result = startup_main._maybe_subscribe_to_bed(_make_args())

        assert result is False
        subscribe.assert_not_called()

    def test_returns_false_when_moniker_attribute_missing(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock(spec=[])

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main, "subscribe_to_bed_sync"
        ) as subscribe:
            result = startup_main._maybe_subscribe_to_bed(_make_args())

        assert result is False
        subscribe.assert_not_called()

    def test_returns_false_when_bbsengine6_member_not_importable(self):
        startup_main = _load_startup_main()

        # Force the import of bbsengine6.member inside the function
        # body to fail. Note: we patch sys.modules so the
        # ``from bbsengine6.member import _threadlocal`` raises.
        import sys
        real_member = sys.modules.get("bbsengine6.member")
        sys.modules["bbsengine6.member"] = None
        try:
            with patch.object(
                startup_main, "subscribe_to_bed_sync"
            ) as subscribe:
                result = startup_main._maybe_subscribe_to_bed(_make_args())
        finally:
            if real_member is not None:
                sys.modules["bbsengine6.member"] = real_member
            else:
                sys.modules.pop("bbsengine6.member", None)

        assert result is False
        subscribe.assert_not_called()


# ---------------------------------------------------------------------------
# _maybe_subscribe_to_bed: bed unreachable
# ---------------------------------------------------------------------------


class TestMaybeSubscribeBedUnreachable:
    """When subscribe_to_bed_sync returns False (bed down or
    misconfigured), the hook should return False and log a debug
    message. The caller treats this as 'fall back to DB polling'."""

    def test_returns_false_when_subscribe_returns_false(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock()
        fake_threadlocal.moniker = "alice"

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main, "subscribe_to_bed_sync", return_value=False
        ), patch(
            "bbsengine6.io.echo"
        ) as echo:
            result = startup_main._maybe_subscribe_to_bed(_make_args())

        assert result is False
        debug_calls = [
            c for c in echo.call_args_list
            if c.kwargs.get("level") == "debug"
        ]
        assert len(debug_calls) >= 1
        msg = debug_calls[0].args[0]
        assert "DB-polling" in msg or "fall back" in msg.lower()

    def test_swallows_exception_from_subscribe(self):
        startup_main = _load_startup_main()

        fake_threadlocal = MagicMock()
        fake_threadlocal.moniker = "alice"

        with patch(
            "bbsengine6.member._threadlocal", fake_threadlocal, create=True
        ), patch.object(
            startup_main,
            "subscribe_to_bed_sync",
            side_effect=RuntimeError("bed exploded"),
        ), patch(
            "bbsengine6.io.echo_traceback"
        ) as trace:
            result = startup_main._maybe_subscribe_to_bed(_make_args())

        assert result is False
        assert trace.call_count == 1


# ---------------------------------------------------------------------------
# main() integration: subscription is invoked at the end of bootstrap
# ---------------------------------------------------------------------------


class TestMainInvokesSubscribe:
    """Verify the wiring: main() should call
    _maybe_subscribe_to_bed() once after the stage loop completes
    successfully, and should NOT call it if the stage loop fails."""

    def test_main_calls_subscribe_on_success(self):
        startup_main = _load_startup_main()

        args = _make_args()
        conn = MagicMock()

        with patch.object(
            startup_main, "_maybe_subscribe_to_bed"
        ) as subscribe, patch.object(
            startup_main.lib, "runmodule", return_value=True
        ), patch.object(
            startup_main.util, "heading"
        ), patch(
            "bbsengine6.io.echo"
        ):
            result = startup_main.main(args, conn=conn)

        assert result is True
        subscribe.assert_called_once_with(args)

    def test_main_skips_subscribe_on_stage_failure(self):
        startup_main = _load_startup_main()

        args = _make_args()
        conn = MagicMock()

        with patch.object(
            startup_main, "_maybe_subscribe_to_bed"
        ) as subscribe, patch.object(
            startup_main.lib, "runmodule", return_value=False
        ), patch.object(
            startup_main.util, "heading"
        ), patch(
            "bbsengine6.io.echo"
        ):
            result = startup_main.main(args, conn=conn)

        # Stage failure -> loop breaks before reaching the
        # _maybe_subscribe_to_bed() call at the end of _work().
        assert result is False
        subscribe.assert_not_called()
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()

    def test_main_commits_on_success(self):
        startup_main = _load_startup_main()

        args = _make_args()
        conn = MagicMock()

        with patch.object(
            startup_main, "_maybe_subscribe_to_bed"
        ), patch.object(
            startup_main.lib, "runmodule", return_value=True
        ), patch.object(
            startup_main.util, "heading"
        ), patch(
            "bbsengine6.io.echo"
        ):
            result = startup_main.main(args, conn=conn)

        assert result is True
        conn.commit.assert_called_once()
