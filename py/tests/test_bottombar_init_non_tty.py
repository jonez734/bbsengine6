"""bottombar.init must not query the terminal when there is no terminal.

startup runs bottombar.init. With no TTY, the {savecursor} tag asks for the cursor position via
termios, which raises termios.error (25, 'Inappropriate ioctl'). init skips the terminal
sequences when stdin or stdout is not a TTY.
"""

from unittest.mock import patch

import pytest

from bbsengine6 import bottombar


@pytest.mark.unit
def test_init_skips_terminal_sequences_when_not_a_tty():
    with patch.object(bottombar.sys.stdin, "isatty", return_value=False), \
         patch.object(bottombar.sys.stdout, "isatty", return_value=False), \
         patch.object(bottombar, "echo") as echo:
        bottombar.init(None)
    assert echo.call_count == 0, echo.call_args_list


@pytest.mark.unit
def test_init_still_sets_the_scroll_region_on_a_tty():
    with patch.object(bottombar.sys.stdin, "isatty", return_value=True), \
         patch.object(bottombar.sys.stdout, "isatty", return_value=True), \
         patch.object(bottombar, "echo") as echo, \
         patch.object(bottombar.terminal, "lines", return_value=24):
        bottombar.init(None)
    assert echo.call_count > 0
