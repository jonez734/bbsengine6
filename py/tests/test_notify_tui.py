# test_notify_tui.py
# Entry point tests for python -m bbsengine6.notify

from bbsengine6.notify.main import buildargs
from bbsengine6.notify import tui


class TestBuildargs:
    """Test buildargs() for notify TUI."""

    def test_buildargs_returns_parser(self):
        parser = buildargs()
        assert parser is not None

    def test_buildargs_has_user_arg(self):
        parser = buildargs()
        args = parser.parse_args([])
        assert hasattr(args, "user")


class TestTuiExports:
    """Test tui module exports."""

    def test_run_exists(self):
        assert hasattr(tui, "run")
        assert callable(tui.run)

    def test_run_until_quit_exists(self):
        assert hasattr(tui, "run_until_quit")
        assert callable(tui.run_until_quit)

    def test_run_forwards_to_run_until_quit(self):
        assert tui.run is not tui.run_until_quit
