"""bottombar.clear() restores the full screen; it is a no-op without a terminal."""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar


@pytest.mark.unit
def test_clear_emits_the_empty_decstbm_reset_on_a_tty():
    with patch.object(bottombar.sys.stdin, "isatty", return_value=True), \
         patch.object(bottombar.sys.stdout, "isatty", return_value=True), \
         patch.object(bottombar, "echo") as echo:
        bottombar.clear()
    echo.assert_called_once()
    assert echo.call_args.args[0] == "{decstbm}"


@pytest.mark.unit
def test_clear_is_a_noop_without_a_terminal():
    with patch.object(bottombar.sys.stdin, "isatty", return_value=False), \
         patch.object(bottombar, "echo") as echo:
        bottombar.clear()
    echo.assert_not_called()
