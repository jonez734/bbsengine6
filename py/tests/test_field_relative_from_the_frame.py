"""The field inside a single-box frame is placed with relative moves from the bottom edge, not an absolute {curpos}.

draw_frame leaves the cursor on the frame's bottom edge. The interior row is the row directly above that edge (the frame
is a top edge, one interior row, and a bottom edge), so the placement is a cursor up of one, then a column move.
"""

import importlib
import unittest
from unittest.mock import patch

util = importlib.import_module("bbsengine6.util")


class TestFieldFromTheBottomEdge(unittest.TestCase):
    def test_the_field_is_one_row_up_from_the_bottom_edge(self):
        frame = util.Frame(title="auth", width=25, top=0, bottom=2)
        self.assertEqual(frame.field_rows_up(), 1)

    def test_the_placement_sends_relative_moves_only(self):
        out = []
        frame = util.Frame(title="auth", width=25, top=0, bottom=2)
        with patch.object(util.io, "echo", side_effect=lambda t="", end="\n", **k: out.append(str(t))):
            frame.place_field()
        self.assertEqual(out, ["{cursorup:1}{cha:2}", "{acs:off}"])
        self.assertFalse(any("{curpos" in t for t in out))


if __name__ == "__main__":
    unittest.main()
