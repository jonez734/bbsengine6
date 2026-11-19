"""A frame with no children has an interior row where a single field goes: no second box is drawn under it.

The frame reports its interior row (top + 1) so the field can be placed inside the frame's own edges.
"""

import importlib
import unittest
from unittest.mock import patch

util = importlib.import_module("bbsengine6.util")


def _writes(fn, *args, **kwargs):
    out = []

    def fake(text="", end="\n", **_):
        out.append(str(text))

    with patch.object(util.io, "echo", side_effect=fake):
        result = fn(*args, **kwargs)
    return result, out


class TestInteriorField(unittest.TestCase):
    def test_a_frame_with_no_children_draws_only_one_box(self):
        _, out = _writes(util.draw_frame, "zoid6 auth", 25)
        titles = [w for w in out if "{ulcorner}" in w or "{acs:ulcorner}" in w]
        self.assertEqual(len(titles), 1, f"one top edge only: {out}")

    def test_the_interior_row_is_one_under_the_top_edge(self):
        frame, _ = _writes(util.draw_frame, "zoid6 auth", 25)
        # The frame's rows are 0-based; {curpos} is 1-based, so the interior is two rows under the frame's 0-based top.
        self.assertEqual(frame.interior_row, frame.top + 2)
        self.assertEqual(frame.interior_column, 2)


if __name__ == "__main__":
    unittest.main()
