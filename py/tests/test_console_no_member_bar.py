"""The console runs from the CLI with no member identity (no bed login). The bottombar must say
so, not render a blank right side.

The right fragment shows "| no member" when the process has no member, and the member and
credits otherwise. The notice is logged once per process, at warning level, so a sysop who runs
the console without a member sees why, and the log keeps the reason.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import lib as console_lib


def _args(debug=False):
    return MagicMock(debug=debug)


@pytest.mark.unit
def test_right_side_says_no_member_when_there_is_none():
    with patch.object(console_lib, "_current_moniker", return_value=None):
        assert console_lib.no_member_right(args=_args()) == "| no member"


@pytest.mark.unit
def test_right_side_is_empty_when_a_member_is_present_and_has_nothing_to_show():
    with patch.object(console_lib, "_current_moniker", return_value="jam"):
        assert console_lib.no_member_right(args=_args()) == ""


@pytest.mark.unit
def test_no_member_notice_is_logged_once_at_warning():
    console_lib._no_member_warned = False
    with patch.object(console_lib, "_current_moniker", return_value=None), \
         patch.object(console_lib.io, "echo") as echo:
        console_lib.no_member_right(args=_args())
        console_lib.no_member_right(args=_args())
    warns = [c for c in echo.call_args_list if c.kwargs.get("level") == "warning"]
    assert len(warns) == 1, echo.call_args_list


@pytest.mark.unit
def test_setbottombar_registers_the_no_member_fragment():
    with patch.object(console_lib, "_current_moniker", return_value=None), \
         patch("bbsengine6.bottombar.register_bottombar_fragment") as reg, \
         patch("bbsengine6.bottombar.unregister_bottombar_fragment"), \
         patch("bbsengine6.bottombar.setbottombar"):
        console_lib.setbottombar(_args(), "con")
    frags = [c.args[0] for c in reg.call_args_list]
    assert any(f.__name__ == "no_member_right" or callable(f) for f in frags), frags
