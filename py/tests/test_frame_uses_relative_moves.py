"""The frame places its join with relative moves, not absolute {curpos}.

draw_frame leaves the cursor on the frame's bottom edge, so the join is written there: a column reset and the join text.
No absolute position is sent, so the placement depends on the cursor the frame drew, not on the screen's coordinates.
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


class TestRelativeJoin(unittest.TestCase):
    def test_extend_frame_sends_no_absolute_position(self):
        frame, _ = _writes(util.draw_frame, "auth", 25)
        _, out = _writes(util.extend_frame, frame, util.Child(title="password"), width=25)
        self.assertFalse(any("{curpos:" in w for w in out), f"absolute curpos in {out}")

    def test_the_join_starts_at_column_one_relative_to_the_bottom_edge(self):
        frame, _ = _writes(util.draw_frame, "auth", 25)
        _, out = _writes(util.extend_frame, frame, util.Child(title="password"), width=25)
        join = out.index("{acs:ltee}{acs:hline:25}{acs:rtee}")
        self.assertEqual(out[join - 1], "{cha:1}")


if __name__ == "__main__":
    unittest.main()
