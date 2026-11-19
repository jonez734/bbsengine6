"""The character-set reset is {acs:off} (ESC(B), no line break). {f6} is a line break in the echo layer.

Using {f6} to reset the set moved the tracked cursor a row down, so a field placed after a frame landed on the border. A
reset must leave the cursor where it is.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

util = importlib.import_module("bbsengine6.util")
common = importlib.import_module("bbsengine6.io.common")
E = importlib.import_module("bbsengine6.io.echo")


class TestResetDoesNotMoveTheCursor(unittest.TestCase):
    def test_the_acs_reset_leaves_the_tracked_row_alone(self):
        st = common._get_terminal_state(); st.cursor_row, st.cursor_col = 3, 27
        common.set_output_stream(pyio.StringIO())
        with patch.object(E.terminal, "lines", return_value=8), patch.object(E.terminal, "columns", return_value=80):
            E.echo("{acs:on}x", end="")
            E.echo("{acs:off}", end="")
            after = (st.cursor_row, st.cursor_col)
        # The x advanced the column once. The reset that follows must not change the row or the column.
        self.assertEqual(after, (3, 30), "the reset leaves the cursor where the x left it")

    def test_place_field_does_not_end_with_a_line_break(self):
        out = []
        frame = util.Frame(title="auth", width=25, top=0, bottom=2)
        with patch.object(util.io, "echo", side_effect=lambda t="", end="\n", **k: out.append(str(t))):
            frame.place_field()
        self.assertFalse(any(t == "{f6}" for t in out), f"place_field ends with a line break: {out}")


if __name__ == "__main__":
    unittest.main()
