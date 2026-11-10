"""Relative cursor moves and {cha} update the engine's tracked cursor, clamped to the terminal.

The tracked position is what inputstring reads for the input origin. A box drawn with relative
moves (cursorup, cursorright, cha) must leave the tracked position where the terminal's cursor is.
"""

import importlib
import io as _io
from unittest.mock import patch

import pytest

from bbsengine6.io import common

pytestmark = pytest.mark.unit

E = importlib.import_module("bbsengine6.io.echo")
INS = importlib.import_module("bbsengine6.io.inputstring")


@pytest.fixture(autouse=True)
def _screen():
    st = common._get_terminal_state()
    st.cursor_row, st.cursor_col = 10, 10
    st.sgr = None
    E._terminal_state_stack.clear()
    with patch.object(E.terminal, "lines", return_value=24), \
         patch.object(E.terminal, "columns", return_value=80):
        yield st
    st.sgr = None


def _echo(text):
    sink = _io.StringIO()
    prev = common._current_output_stream
    common.set_output_stream(sink)
    try:
        E.echo(text, end="", flush=True)
    finally:
        common.set_output_stream(prev)


def test_cursor_up_moves_the_tracked_row_up(_screen):
    _echo("{cursorup:3}")
    assert _screen.cursor_row == 7


def test_cursor_down_moves_the_tracked_row_down(_screen):
    _echo("{cud:2}")
    assert _screen.cursor_row == 12


def test_cursor_right_moves_the_tracked_column_right(_screen):
    _echo("{cursorright:4}")
    assert _screen.cursor_col == 14


def test_cursor_left_moves_the_tracked_column_left(_screen):
    _echo("{cub:3}")
    assert _screen.cursor_col == 7


def test_moves_clamp_at_the_top_and_left_edges(_screen):
    _screen.cursor_row, _screen.cursor_col = 2, 2
    _echo("{cursorup:9}{cursorleft:9}")
    assert (_screen.cursor_row, _screen.cursor_col) == (1, 1)


def test_moves_clamp_at_the_bottom_and_right_edges(_screen):
    _screen.cursor_row, _screen.cursor_col = 22, 78
    _echo("{cud:9}{cursorright:9}")
    assert (_screen.cursor_row, _screen.cursor_col) == (24, 80)


def test_cha_sets_the_tracked_column_one_based(_screen):
    _echo("{cha:1}")
    assert _screen.cursor_col == 1
    _echo("{cha:20}")
    assert _screen.cursor_col == 20


def test_cha_clamps_to_the_terminal_width(_screen):
    _echo("{cha:999}")
    assert _screen.cursor_col == 80


def test_unknown_size_skips_clamping_rather_than_guessing(_screen):
    with patch.object(E.terminal, "lines", return_value=None), \
         patch.object(E.terminal, "columns", return_value=None):
        _echo("{cud:50}")
    assert _screen.cursor_row == 60


def test_box_then_prompt_puts_the_input_inside_the_box(_screen):
    # The demo: draw a box, move into it with relative moves, then prompt. The input origin must
    # be the box interior (row 10, column 3), not the box corner.
    _screen.cursor_row, _screen.cursor_col = 12, 1
    _echo("{acs:ulcorner}{acs:hline:5}{acs:urcorner}")
    _echo("{acs:llcorner}{acs:hline:5}{acs:lrcorner}")
    _echo("{cursorup}{cha:1}{cursorright:2}")
    assert (_screen.cursor_row, _screen.cursor_col) == (11, 3)
    origin = INS._input_origin(11, 3, "inputstring_box: ")
    assert origin == (11, 3)
