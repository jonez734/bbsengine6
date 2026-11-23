"""draw_frame(height=N) gives the frame's own interior N rows, and place_row moves between them with relative moves.

The frame does not read the terminal's cursor position. It keeps its own row: after draw_frame the cursor is on the bottom
edge (the frame's row ``bottom``). place_row(i) moves from that row to interior row i and records it. A field read on a row
ends with the line break, so the caller reports it with after_field(): the cursor is then one row below the field.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


def _draw(height):
    out = pyio.StringIO()
    common.set_output_stream(out)
    st = common._get_terminal_state()
    st.cursor_row, st.cursor_col, st.acs = 1, 1, False
    with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
        frame = util.draw_frame("zoid6 auth", 25, height=height)
    return frame, out.getvalue()


def _moves(fn):
    out = []
    with patch.object(util.io, "echo", side_effect=lambda t="", end="\n", **k: out.append(str(t))):
        fn()
    return out


class TestInteriorRows(unittest.TestCase):
    def test_height_one_is_the_single_row_frame(self):
        frame, _ = _draw(1)
        self.assertEqual(frame.bottom, 2)

    def test_height_two_adds_a_row_inside_the_frame(self):
        frame, _ = _draw(2)
        self.assertEqual(frame.bottom, 3)

    def test_interior_rows_are_listed_top_to_bottom(self):
        frame, _ = _draw(2)
        self.assertEqual(frame.interior_rows(), [2, 3])  # 1-based screen rows of the two interior lines

    def test_the_frame_starts_with_the_cursor_on_the_bottom_edge(self):
        frame, _ = _draw(2)
        self.assertEqual(frame.cursor_at, frame.bottom)


class TestPlaceRow(unittest.TestCase):
    def test_the_first_row_is_two_up_from_the_bottom_edge(self):
        frame, _ = _draw(2)
        moves = _moves(lambda: frame.place_row(0))
        self.assertEqual(moves[:2], ["{cursorup:2}", "{cha:3}"])

    def test_the_last_row_is_one_up_from_the_bottom_edge(self):
        frame, _ = _draw(2)
        moves = _moves(lambda: frame.place_row(1))
        self.assertEqual(moves[:2], ["{cursorup:1}", "{cha:3}"])

    def test_placing_the_same_row_twice_moves_nothing_vertically(self):
        frame, _ = _draw(2)
        _moves(lambda: frame.place_row(0))
        moves = _moves(lambda: frame.place_row(0))
        self.assertEqual(moves[0], "{cha:3}", moves)


class TestAfterAField(unittest.TestCase):
    """A field's Enter leaves the cursor one row below the field (measured in a pty with a plain read)."""

    def test_after_a_field_the_cursor_is_one_row_below_it(self):
        frame, _ = _draw(2)
        _moves(lambda: frame.place_row(0))   # moniker: interior row 0, screen/frame row 1
        _moves(lambda: frame.after_field())
        self.assertEqual(frame.cursor_at, 2)  # one row below the field

    def test_the_password_row_is_reached_with_no_vertical_move_after_the_moniker_read(self):
        frame, _ = _draw(2)
        _moves(lambda: frame.place_row(0))
        _moves(lambda: frame.after_field())  # cursor is now on interior row 1
        moves = _moves(lambda: frame.place_row(1))
        self.assertEqual(moves[0], "{cha:3}", moves)


class TestFrameAtAnyRow(unittest.TestCase):
    """The moves depend only on the frame's own rows, so a frame drawn lower on the screen moves the same way."""

    def test_the_first_row_is_still_two_up_when_the_frame_starts_lower(self):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 5, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            frame = util.draw_frame("zoid6 auth", 25, height=2)
        moves = _moves(lambda: frame.place_row(0))
        self.assertEqual(moves[0], "{cursorup:2}", moves)


if __name__ == "__main__":
    unittest.main()
