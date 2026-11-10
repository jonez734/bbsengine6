"""The input window after an {f6} is the full row, not the row minus the prompt.

The input origin is where the prompt left the tracked cursor. Without a break the prompt shares
the input row, so the text window is max_width minus the prompt's visible width. After an {f6} the
prompt's text is on the row below, so the window is still reduced by the text drawn on that row
(which is the prompt's text after the break), not by the prompt on the row above.
"""

import importlib
import io as _io
from unittest.mock import patch

import pytest

from bbsengine6.io import common

pytestmark = pytest.mark.unit

INS = importlib.import_module("bbsengine6.io.inputstring")
E = importlib.import_module("bbsengine6.io.echo")


def _run(prompt, max_width, start=(5, 1)):
    """Run inputstring with Enter pressed at once. Return (origin, max_width used, text_col)."""
    captured = {}
    real_origin = INS.input_origin

    def spy_origin(p, r, c, w):
        out = real_origin(p, r, c, w)
        captured["origin"] = out[:2]
        return out

    common._get_terminal_state().sgr = None
    sink = _io.StringIO()
    prev = common._current_output_stream
    common.set_output_stream(sink)
    try:
        with patch.object(E.terminal, "lines", return_value=24), \
             patch.object(E.terminal, "columns", return_value=80), \
             patch.object(INS, "get_cursor_position", return_value=start), \
             patch.object(INS, "getch", return_value="KEY_ENTER"), \
             patch.object(INS, "begin_raw_session"), patch.object(INS, "end_raw_session"), \
             patch.object(INS, "mouse_state_push"), patch.object(INS, "mouse_state_pop"), \
             patch.object(INS, "bracketed_paste_on"), patch.object(INS, "bracketed_paste_off"), \
             patch.object(INS, "_show_mode"), \
             patch.object(INS, "input_origin", side_effect=spy_origin):
            INS.inputstring(prompt, "", max_width=max_width, bottombar=False)
    finally:
        common.set_output_stream(prev)
    return captured["origin"]


def test_no_break_the_input_starts_after_the_prompt_on_its_row():
    origin = _run("inputstring_box: ", 25, start=(5, 1))
    assert origin == (5, 1 + len("inputstring_box: "))


def test_f6_puts_the_input_on_the_row_below_after_the_prompt_text():
    # The tracked cursor is on the row below the break and after the text drawn there.
    origin = _run("status{f6}input: ", 25, start=(5, 1))
    assert origin == (6, len("input: "))


def test_f6_input_starts_after_the_text_on_its_own_row_not_the_row_above():
    # A long prompt on the row above does not move the input: it starts after the text on the
    # input's own row, which here is "in: " (column 4).
    long_top = "x" * 30
    origin_top = _run(f"{long_top}{{f6}}in: ", 25, start=(5, 1))
    assert origin_top == (6, len("in: "))


def _blank_window(prompt, max_width, start=(5, 1)):
    """The blank text window inputstring writes first, as (row, col, width)."""
    import re

    sink = _io.StringIO()
    prev = common._current_output_stream
    common.set_output_stream(sink)
    try:
        with patch.object(E.terminal, "lines", return_value=24), \
             patch.object(E.terminal, "columns", return_value=80), \
             patch.object(INS, "get_cursor_position", return_value=start), \
             patch.object(INS, "getch", return_value="KEY_ENTER"), \
             patch.object(INS, "begin_raw_session"), patch.object(INS, "end_raw_session"), \
             patch.object(INS, "mouse_state_push"), patch.object(INS, "mouse_state_pop"), \
             patch.object(INS, "bracketed_paste_on"), patch.object(INS, "bracketed_paste_off"), \
             patch.object(INS, "_show_mode"):
            INS.inputstring(prompt, "", max_width=max_width, bottombar=False)
    finally:
        common.set_output_stream(prev)
    m = re.search(r"\x1b\[(\d+);(\d+)H( +)", sink.getvalue())
    assert m, sink.getvalue()
    return int(m.group(1)), int(m.group(2)), len(m.group(3))


def test_f6_window_is_full_width_and_starts_at_the_input_origin():
    row, col, width = _blank_window("status{f6}input: ", 25, start=(5, 1))
    assert (row, col) == (6, len("input: "))
    assert width == 25


def test_no_break_window_is_max_width_minus_the_prompt():
    row, col, width = _blank_window("inputstring_box: ", 25, start=(5, 1))
    assert width == 25 - len("inputstring_box: ")
