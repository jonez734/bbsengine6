"""inputstring starts the input where the prompt left the cursor.

The input origin used to be start_col + rendered_length(prompt): a width count, blind to {f6},
ACS box drawing and {curpos}. The origin is now the tracked cursor after the prompt is drawn.
After an {f6} it is the row below, at the tracked column (the indent, 0 by default).
"""

import re
from unittest.mock import patch

import pytest

import importlib

from bbsengine6.io import common

# The package re-exports the inputstring function under the same name, so import the module itself.
ins = importlib.import_module("bbsengine6.io.inputstring")

pytestmark = pytest.mark.unit

CURPOS = re.compile(r"\{curpos:(\d+),(\d+)\}")


def _input_origin(prompt, start=(5, 1)):
    """Run inputstring with Enter pressed at once; return the (row, col) it put the input at.

    The real echo runs, so the engine's tracked cursor is what inputstring reads. Only the terminal
    I/O is stubbed: the output is captured, and the position query returns the start.
    """
    common._terminal_state.cursor_row = start[0]
    common._terminal_state.cursor_col = start[1]
    import io as _io

    sink = _io.StringIO()
    previous = common._current_output_stream
    common.set_output_stream(sink)
    captured = {}
    real_origin = ins.input_origin

    def spy_origin(prompt_text, start_row, start_col, max_width):
        result = real_origin(prompt_text, start_row, start_col, max_width)
        captured["origin"] = result[:2]
        return result
    with patch.object(ins, "getch", return_value="KEY_ENTER"), \
         patch.object(ins, "begin_raw_session", return_value=None), \
         patch.object(ins, "end_raw_session", return_value=None), \
         patch.object(ins, "mouse_state_push", return_value=None), \
         patch.object(ins, "mouse_state_pop", return_value=None), \
         patch.object(ins, "bracketed_paste_on", return_value=None), \
         patch.object(ins, "bracketed_paste_off", return_value=None), \
         patch.object(ins, "get_cursor_position", return_value=start), \
         patch.object(ins, "input_origin", side_effect=spy_origin):
        try:
            ins.inputstring(prompt, "")
        finally:
            common.set_output_stream(previous)
    return captured["origin"]


def test_plain_prompt_keeps_the_width_origin():
    # No {f6}: the origin is the start column plus the prompt's width, exactly as before.
    row, col = _input_origin("name: ", start=(5, 1))
    assert (row, col) == (5, 1 + len("name: "))


def test_f6_puts_the_input_on_the_row_below_at_column_zero():
    # After an {f6} the cursor is at column 0 of the next row, so the input starts there.
    row, col = _input_origin("status{f6}casino_client: ", start=(5, 1))
    assert (row, col) == (6, len("casino_client: "))


def test_input_follows_the_prompt_not_the_whole_width():
    # The 36-column width of status+prompt must not push the input right of the input line.
    row, col = _input_origin("[jam] Balance: 100000{f6}casino_client: ", start=(5, 1))
    assert col == len("casino_client: ")
    assert col < 36


def test_f6_honours_the_indent():
    # With an indent set, the tracked column after an {f6} is the indent, so the input follows it.
    saved = common._terminal_state.indent if hasattr(common, "_terminal_state") else None
    state = getattr(common, "_terminal_state", None)
    if state is None:
        pytest.skip("terminal state not exposed")
    old = state.indent
    try:
        state.indent = 4
        row, col = _input_origin("status{f6}input: ", start=(5, 1))
    finally:
        state.indent = old
    assert (row, col) == (6, 4 + len("input: "))


def test_cursor_moved_by_curpos_before_the_prompt_is_followed():
    # A {curpos} written before the prompt moves the origin with it.
    row, col = _input_origin("{curpos:9,20}name: ", start=(5, 1))
    assert (row, col) == (9, 20 + len("name: "))



def test_box_interior_field_ends_at_the_interior_edge():
    # The demo box is drawn at column 1 with a 25-wide interior (columns 2-26). The prompt starts
    # at column 3 and is drawn through echo, so the tracked cursor is where the input follows. The
    # field is the room from column 3 to column 26: 24 columns. The 17-column prompt leaves a
    # 7-column window, from column 20 through column 26.
    import io as _io

    prompt = "inputstring_box: "
    sink = _io.StringIO()
    previous = common._current_output_stream
    common.set_output_stream(sink)
    try:
        ins.echo(f"{{curpos:11,3}}{prompt}", end="", flush=True)
        row, col, window = ins.input_origin(prompt, 11, 3, 24)
    finally:
        common.set_output_stream(previous)
    assert (row, col) == (11, 3 + len(prompt))
    assert window == 24 - len(prompt) == 7
    assert col + window - 1 == 26
