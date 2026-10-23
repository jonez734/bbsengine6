"""The bottombar redraws when the unread count changes, not once per process.

_update_bottombar_on_notification used to set a session flag and never clear it, so after the first
notification every later change was skipped and the bar kept the first count.
"""

import importlib
from unittest.mock import patch

import pytest

getch = importlib.import_module("bbsengine6.io.getch")


@pytest.fixture(autouse=True)
def _reset_flag():
    getch._bottombar_updated_this_session = ""
    yield
    getch._bottombar_updated_this_session = ""


def _draw(status):
    with patch.object(getch.screen, "get_notification_status", return_value=status), \
         patch.object(getch, "echo") as echo:
        result = getch._update_bottombar_on_notification()
    return result, " ".join(str(c.args[0]) for c in echo.call_args_list if c.args)


@pytest.mark.unit
def test_second_change_redraws_the_bar_with_the_new_count():
    first, _ = _draw("F2: messages (3)")
    second, text = _draw("F2: messages (4)")
    assert first is True
    assert second is True, "a changed count must redraw the bar"
    assert "(4)" in text


@pytest.mark.unit
def test_unchanged_count_is_not_redrawn():
    _draw("F2: messages (3)")
    result, _ = _draw("F2: messages (3)")
    assert result is False


@pytest.mark.unit
def test_empty_status_clears_nothing_and_draws_nothing():
    result, text = _draw("")
    assert text == ""
