"""place_child moves to a child's field and records the row the cursor is on, so a later place_row counts from there.

place_child's own moves are unchanged (existing tests pin them). The only addition is cursor_at, which place_row reads.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


def _moves(fn):
    out = []
    with patch.object(util.io, "echo", side_effect=lambda t="", end="\n", **k: out.append(str(t))):
        fn()
    return out


class TestPlaceChildRecordsTheRow(unittest.TestCase):
    def _frame(self):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 1, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            return util.draw_frame("zoid6 auth", 25, children=[util.Child(title="moniker"), util.Child(title="password", gap=0)])

    def test_place_child_records_the_interior_row_it_moved_to(self):
        frame = self._frame()
        _moves(lambda: frame.place_child(0))
        self.assertEqual(frame.cursor_at, frame.children[0].top + 1)

    def test_place_row_after_place_child_counts_from_where_place_child_left_the_cursor(self):
        frame = self._frame()
        _moves(lambda: frame.place_child(0))  # cursor on the moniker child's interior row (frame row 5)
        # place_row addresses the frame's own interior (frame row 1), so it moves from row 5 to row 1: up 4.
        moves = _moves(lambda: frame.place_row(0))
        self.assertEqual(moves[0], "{cursorup:4}", moves)

    def test_place_child_emits_the_same_moves_as_before(self):
        frame = self._frame()
        moves = _moves(lambda: frame.place_child(0))
        self.assertEqual(moves[0], f"{{cursorup:{frame.bottom - (frame.children[0].top + 1)}}}{{cha:3}}")


if __name__ == "__main__":
    unittest.main()
