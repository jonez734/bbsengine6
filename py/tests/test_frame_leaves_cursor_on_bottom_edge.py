"""draw_frame leaves the cursor on its bottom edge, so the field is placed one row up from there.

The {f6} that resets the character set must not move the cursor off the bottom edge: the echo layer counts {f6} as a line
end, so a trailing {f6} put the cursor one row below the frame and the field landed on the border.
"""

import importlib
import unittest
from unittest.mock import patch

util = importlib.import_module("bbsengine6.util")
common = importlib.import_module("bbsengine6.io.common")
E = importlib.import_module("bbsengine6.io.echo")


class TestCursorStaysOnTheBottomEdge(unittest.TestCase):
    def test_after_draw_frame_the_tracked_row_is_the_bottom_edge(self):
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col = 22, 1
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            util.draw_frame("zoid6 auth", 25)
        self.assertEqual(st.cursor_row, 24, "a frame drawn from row 22 ends on its bottom edge, row 24")


if __name__ == "__main__":
    unittest.main()
