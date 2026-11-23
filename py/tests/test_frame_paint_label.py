"""Frame.paint_label writes a label on an interior row, then returns the cursor to where it was.

Relative moves only: to the row, write the label at the field column, then back to the frame's cursor row.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


class TestPaintLabel(unittest.TestCase):
    def _frame(self):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 1, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            return util.draw_frame("zoid6 auth", 25, height=2)

    def test_the_label_is_written_on_its_row_and_the_cursor_comes_back(self):
        frame = self._frame()
        before = frame.cursor_at
        writes = []
        with patch.object(util.io, "echo", side_effect=lambda t="", *a, **k: writes.append(str(t))):
            frame.paint_label(1, "password:")
        self.assertTrue(any("password:" in w for w in writes), writes)
        self.assertEqual(frame.cursor_at, before, "the cursor is back on the row it was on")

    def test_a_label_on_the_first_row_is_written_without_disturbing_the_frame(self):
        frame = self._frame()
        writes = []
        with patch.object(util.io, "echo", side_effect=lambda t="", *a, **k: writes.append(str(t))):
            frame.paint_label(0, "moniker:")
        self.assertTrue(any("moniker:" in w for w in writes), writes)
        self.assertNotIn("{curpos", "".join(writes))


if __name__ == "__main__":
    unittest.main()
