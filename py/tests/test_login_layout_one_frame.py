"""The sign-in layout is one frame holding both fields, as in tk/login.py: moniker and password in one box.

The demo no longer grows a frame to hold the password. draw_frame draws both children, and place_child addresses each
field inside the same frame.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


def _draw(children):
    out = pyio.StringIO()
    common.set_output_stream(out)
    st = common._get_terminal_state()
    st.cursor_row, st.cursor_col, st.acs = 1, 1, False
    with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
        frame = util.draw_frame("zoid6 auth", 25, children=children)
    return frame, out.getvalue()


class TestOneFrameTwoFields(unittest.TestCase):
    def test_both_fields_are_inside_the_one_frame(self):
        frame, _ = _draw([util.Child(title="moniker"), util.Child(title="password", gap=0)])
        top, bottom = frame.top, frame.bottom
        for field in frame.children:
            self.assertGreater(field.top, top)
            self.assertLessEqual(field.bottom, bottom)

    def test_the_password_field_is_not_on_its_own_frame(self):
        frame, _ = _draw([util.Child(title="moniker"), util.Child(title="password", gap=0)])
        # One frame: the password child is joined under the moniker and the frame's bottom closes after both fields.
        self.assertEqual(len(frame.children), 2)
        self.assertEqual(frame.bottom, frame.children[-1].bottom)

    def test_each_field_places_its_cursor_inside_the_frame(self):
        frame, _ = _draw([util.Child(title="moniker"), util.Child(title="password", gap=0)])
        for index in range(len(frame.children)):
            out = pyio.StringIO()
            common.set_output_stream(out)
            with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
                frame.place_child(index)
            self.assertNotIn("{curpos", out.getvalue())


if __name__ == "__main__":
    unittest.main()
