"""Interior content starts one space after the left border: the border is column 1, a space is column 2, content is 3.

Every interior column, child column, and cursor move that places text uses the same value, so the rule is pinned in one
place (Frame.interior_column) and checked against the child columns.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


class TestOneSpace(unittest.TestCase):
    def _frame(self, children=()):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 1, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            return util.draw_frame("zoid6 auth", 25, height=2, children=children)

    def test_interior_text_starts_at_column_three(self):
        self.assertEqual(self._frame().interior_column, 3)

    def test_a_child_field_starts_at_column_three(self):
        frame = self._frame(children=[util.Child(title="moniker")])
        self.assertEqual(frame.children[0].column, 3)


if __name__ == "__main__":
    unittest.main()
