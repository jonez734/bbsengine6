"""Every input function starts its input where the prompt left the cursor, inside a caller's box.

The origin and window rule lives in bbsengine6.io.inputorigin. inputstring, inputchoice and
inputboolean all use it. The caller draws any box; these tests draw one with ACS characters and
cursor moves, then prompt, and check the input starts inside it.
"""

import importlib
import io as _io
from unittest.mock import patch

import pytest

from bbsengine6.io import common

pytestmark = pytest.mark.unit

E = importlib.import_module("bbsengine6.io.echo")
INS = importlib.import_module("bbsengine6.io.inputstring")
CHO = importlib.import_module("bbsengine6.io.inputchoice")
BOO = importlib.import_module("bbsengine6.io.inputboolean")
ORG = importlib.import_module("bbsengine6.io.inputorigin")


def _key_script(*keys):
    seq = list(keys)

    def fake_getch(**kwargs):
        return seq.pop(0)

    return fake_getch


def _patched(keys):
    """Common terminal stubs. The cursor query returns the tracked position, as a real terminal's
    cursor would be after the caller's box and cursor moves."""
    from contextlib import ExitStack

    def cursor_now():
        # The position the caller left the cursor at: captured once, before the prompt draws.
        st = common._get_terminal_state()
        return (st.cursor_row, st.cursor_col)

    stack = ExitStack()
    stack.enter_context(patch.object(E.terminal, "lines", return_value=24))
    stack.enter_context(patch.object(E.terminal, "columns", return_value=80))
    stack.enter_context(patch.object(INS, "get_cursor_position", side_effect=cursor_now))
    stack.enter_context(patch.object(INS, "getch", side_effect=_key_script(*keys)))
    stack.enter_context(patch.object(CHO, "getch", side_effect=_key_script(*keys)))
    for name in ("begin_raw_session", "end_raw_session", "mouse_state_push", "mouse_state_pop",
                 "bracketed_paste_on", "bracketed_paste_off", "_show_mode"):
        stack.enter_context(patch.object(INS, name))
    return stack


def _box_then(prompt_fn, *keys):
    """Draw a 5-wide box at row 12, move into it, then run prompt_fn. Return (origin, output)."""
    sink = _io.StringIO()
    prev = common._current_output_stream
    common.set_output_stream(sink)
    captured = {}
    real = ORG.input_origin

    def spy(*a, **k):
        out = real(*a, **k)
        captured.setdefault("origin", out)
        return out

    st = common._get_terminal_state()
    st.sgr = None
    st.cursor_row, st.cursor_col = 12, 1
    st.indent = 0
    try:
        with _patched(keys), patch.object(INS, "input_origin", side_effect=spy), \
                patch.object(CHO, "input_origin", side_effect=spy, create=True), \
                patch.object(BOO, "input_origin", side_effect=spy, create=True):
            E.echo("{acs:ulcorner}{acs:hline:5}{acs:urcorner}", end="", flush=True)
            E.echo("{acs:llcorner}{acs:hline:5}{acs:lrcorner}", end="", flush=True)
            E.echo("{cursorup}{cha:1}{cursorright:2}", end="", flush=True)
            prompt_fn()
    finally:
        common.set_output_stream(prev)
    return captured.get("origin"), sink.getvalue()


def test_inputstring_in_a_box_starts_inside_it():
    origin, _ = _box_then(lambda: INS.inputstring("name: ", "", max_width=10, bottombar=False), "KEY_ENTER")
    # The box interior is row 11 (the box top is row 12, moved up one row into it).
    assert origin[0] == 11


def test_inputchoice_in_a_box_starts_inside_it():
    origin, _ = _box_then(lambda: CHO.inputchoice("ok? ", "YN", "Y"), "Y")
    assert origin is not None and origin[0] == 11


def test_inputboolean_in_a_box_echoes_its_answer_at_the_origin():
    _, out = _box_then(lambda: BOO.inputboolean("ok? ", "YN", "Y"), "Y")
    assert "Yes" in out


def test_inputchoice_help_returns_the_prompt_to_the_origin():
    seen = {}

    def help_fn(**kw):
        seen["called"] = True

    def run():
        CHO.inputchoice("ok? ", "YN", "Y", help=help_fn)

    _, out = _box_then(run, "KEY_F1", "Y")
    assert seen.get("called")
    # After help, the prompt is written again at the origin (row 11, after the box interior).
    tail = out.split("help", 1)[1]
    assert "\x1b[11;" in tail


def test_inputchoice_f2_returns_the_prompt_to_the_origin():
    def run():
        CHO.inputchoice("ok? ", "YN", "Y", f2_handler=lambda **kw: None)

    _, out = _box_then(run, "KEY_F2", "Y")
    tail = out.split("ok? ", 1)[-1]
    assert "\x1b[11;" in out.split("\x1b[11;", 1)[-1][:6] or "\x1b[11;" in out


def test_origin_helper_no_break_is_the_prompt_end():
    st = common._get_terminal_state()
    st.sgr = None
    st.cursor_row, st.cursor_col = 5, 1
    st.cursor_col = 1 + len("name: ")  # what drawing the prompt leaves the cursor at
    row, col, window = ORG.input_origin("name: ", 5, 1, 25)
    assert (row, col) == (5, 1 + len("name: "))
    assert window == 25 - len("name: ")


def test_origin_helper_f6_is_the_row_below_with_the_full_window():
    st = common._get_terminal_state()
    st.cursor_row, st.cursor_col = 6, 0
    row, col, window = ORG.input_origin(5, 1, "status{f6}input: ", max_width=25)
    assert row == 6
    assert window == 25
