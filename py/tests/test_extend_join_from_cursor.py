"""extend_frame paints the join from the cursor, with no save, restore, or absolute move.

After the moniker's Enter the cursor is on the moniker box's bottom border. The join replaces that row: a column reset,
then the ltee/hline/rtee run. The password child is drawn on the row below it.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


class TestJoinFromCursor(unittest.TestCase):
    def _extend_on_the_border(self):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 1, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            f = util.draw_frame("zoid6 auth", 25, children=[util.Child(title="moniker")])
            f.place_child(0)
            mark = len(out.getvalue())
            frame = util.extend_frame(f, util.Child(title="password"), width=25)
        return out.getvalue()[mark:], frame

    def test_no_save_restore_or_absolute_move(self):
        tail, _ = self._extend_on_the_border()
        for bad in ("\x1b7", "\x1b8", "{decsc}", "{decrc}", "{curpos"):
            self.assertNotIn(bad, tail)

    def test_the_join_starts_at_the_cursor_with_a_column_reset(self):
        tail, _ = self._extend_on_the_border()
        self.assertTrue(tail.startswith("\x1b[1G"), repr(tail[:24]))
        self.assertIn("\x1b(0t\x1b(B", tail)  # the rtee of the join: the join is painted here

    def test_the_child_is_drawn_on_the_row_below_the_join(self):
        tail, _ = self._extend_on_the_border()
        join_end = tail.index("\x1b(0t\x1b(B") + len("\x1b(0t\x1b(B")
        after_join = tail[join_end:]
        # The child's top edge is the next row: a line break comes before its vline on the following row.
        self.assertIn("\n", after_join[:40], repr(after_join[:60]))

    def test_the_password_child_is_below_the_join(self):
        _, frame = self._extend_on_the_border()
        join_row = frame.children[0].bottom
        self.assertEqual(frame.children[-1].top, join_row + 1)


if __name__ == "__main__":
    unittest.main()
