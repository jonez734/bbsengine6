"""{decsc}/{decrc} save and restore the colour and attributes, not only the cursor.

A save records the SGR state in effect at that point; a restore re-emits it, so the next text is
drawn in the saved colour. The bottom bar's paint between a save and a restore leaves the caller's
colour alone.
"""

import importlib
import io as _io
from unittest.mock import patch

import pytest

from bbsengine6.io import common
from bbsengine6.io import sgr_state

pytestmark = pytest.mark.unit

E = importlib.import_module("bbsengine6.io.echo")
RED = "\x1b[38;2;136;0;0m"


@pytest.fixture(autouse=True)
def _fresh_terminal_state():
    """Each scenario starts with no saved colour, so the tests do not depend on order."""
    st = common._get_terminal_state()
    st.sgr = None
    st.cursor_row, st.cursor_col = 3, 4
    E._terminal_state_stack.clear()
    yield
    st.sgr = None
    E._terminal_state_stack.clear()


def _run(*steps):
    sink = _io.StringIO()
    prev = common._current_output_stream
    common.set_output_stream(sink)
    try:
        with patch.object(E, "get_cursor_position", return_value=(3, 4)):
            for text in steps:
                E.echo(text, end="", flush=True)
    finally:
        common.set_output_stream(prev)
    return sink.getvalue()


def test_restore_reemits_the_saved_colour_before_the_next_text():
    out = _run("{red}A{decsc}", "{green}B{decrc}", "C")
    # The text after the restore is drawn in the saved colour, not the colour written last.
    assert out.endswith("\x1b[3;4H\x1b[0;38;2;136;0;0mC")


def test_restore_puts_back_the_saved_attributes():
    out = _run("{bold}A{decsc}", "{/bold}B{decrc}", "C")
    assert "\x1b[0;1" in out.split("\x1b[3;4H")[-1]


def test_a_bar_paint_between_save_and_restore_keeps_the_callers_colour():
    out = _run(
        "{red}A{decsc}",
        "{savecursor}{bottombarcolor}BAR{restorecursor}",
        "C",
    )
    # The bar's own colour is written only inside its paint; the text after the paint is the
    # caller's colour, re-emitted by the restore, with no reset in between.
    tail = out.split("BAR", 1)[1]
    assert tail == "\x1b[3;4H\x1b[0;38;2;136;0;0mC"


def test_sgr_state_tracks_colour_and_attributes():
    st = sgr_state.apply(sgr_state.EMPTY, "\x1b[1m\x1b[31m\x1b[44m")
    assert "bold" in st.attrs and st.fg == ("31",) and st.bg == ("44",)
    st = sgr_state.apply(st, "\x1b[22m\x1b[0m")
    assert st == sgr_state.EMPTY


def test_sgr_emit_rebuilds_the_state():
    st = sgr_state.apply(sgr_state.EMPTY, "\x1b[1m\x1b[38;2;10;20;30m")
    assert sgr_state.apply(sgr_state.EMPTY, sgr_state.emit(st)) == st
