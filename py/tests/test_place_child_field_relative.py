"""Frame.place_child(index) moves the cursor to a child's interior with relative moves only.

After draw_frame or extend_frame the cursor is on the frame's bottom edge. A child's interior row is
above that edge, so the move is a cursor up by the rows between, then a column move. No {curpos}.
"""

import importlib
import unittest
from unittest.mock import patch

util = importlib.import_module("bbsengine6.util")


def _capture(fn):
    out = []
    with patch.object(util.io, "echo", side_effect=lambda t="", end="\n", **k: out.append(str(t))):
        fn()
    return out


class TestPlaceChildRelative(unittest.TestCase):
    def test_second_child_is_placed_up_from_the_bottom_edge(self):
        # Frame at rows 0..2 (top, one interior row, bottom), then a child at rows 2..4 (its own top shares row 2).
        frame = util.Frame(title="auth", width=25, top=0, bottom=4,
                           children=[util.ChildPlace(title="moniker", top=0, bottom=2, column=2),
                                     util.ChildPlace(title="password", top=2, bottom=4, column=2)])
        out = _capture(lambda: frame.place_child(1))
        # The password interior is row 3; the cursor is on row 4 (the bottom edge): up 1, then column 2.
        self.assertEqual(out, ["{cursorup:1}{cha:2}", "{acs:off}"])

    def test_first_child_is_placed_from_the_bottom_edge_when_it_is_the_last(self):
        frame = util.Frame(title="auth", width=25, top=0, bottom=2,
                           children=[util.ChildPlace(title="moniker", top=0, bottom=2, column=2)])
        out = _capture(lambda: frame.place_child(0))
        self.assertEqual(out, ["{cursorup:1}{cha:2}", "{acs:off}"])

    def test_no_absolute_move_is_sent(self):
        frame = util.Frame(title="auth", width=25, top=0, bottom=4,
                           children=[util.ChildPlace(title="moniker", top=0, bottom=2, column=2),
                                     util.ChildPlace(title="password", top=2, bottom=4, column=2)])
        out = _capture(lambda: frame.place_child(1))
        self.assertFalse(any("{curpos" in t for t in out), out)


if __name__ == "__main__":
    unittest.main()
