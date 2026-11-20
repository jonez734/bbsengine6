"""draw_frame without height, and the Frame dataclass, stay compatible with the committed HEAD.

The golden bytes in golden_frame_head.py were captured from HEAD before the frame gained height and place_row. Existing
callers depend on: the exact bytes of draw_frame(title, width) with and without a child, the geometry of those frames,
and positional construction of Frame(title, width, top, bottom, ...).
"""

import dataclasses
import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

from golden_frame_head import BYTES_NO_CHILDREN, BYTES_ONE_CHILD, GEOM_NO_CHILDREN, GEOM_ONE_CHILD

E = importlib.import_module("bbsengine6.io.echo")
util = importlib.import_module("bbsengine6.util")


def _draw(**kwargs):
    out = pyio.StringIO()
    common.set_output_stream(out)
    st = common._get_terminal_state()
    st.cursor_row, st.cursor_col, st.acs = 1, 1, False
    with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
        frame = util.draw_frame("zoid6 auth", 25, **kwargs)
    return frame, out.getvalue()


class TestGoldenBytes(unittest.TestCase):
    def test_draw_frame_without_children_emits_the_committed_bytes(self):
        _, out = _draw()
        self.assertEqual(out, BYTES_NO_CHILDREN)

    def test_draw_frame_with_one_child_emits_the_committed_bytes(self):
        out = pyio.StringIO()
        common.set_output_stream(out)
        st = common._get_terminal_state()
        st.cursor_row, st.cursor_col, st.acs = 1, 1, False
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            util.draw_frame("zoid6 auth", 25, children=[util.Child(title="moniker")])
        self.assertEqual(out.getvalue(), BYTES_ONE_CHILD)


class TestGoldenGeometry(unittest.TestCase):
    def test_no_children_geometry_is_unchanged(self):
        frame, _ = _draw()
        self.assertEqual(f"{frame.top!r} {frame.bottom!r} {frame.width!r} {len(frame.children)!r}", GEOM_NO_CHILDREN)

    def test_one_child_geometry_is_unchanged(self):
        frame, _ = _draw(children=[util.Child(title="moniker")])
        got = f"{frame.top!r} {frame.bottom!r} {frame.width!r} {[(c.top, c.bottom, c.column) for c in frame.children]!r}"
        self.assertEqual(got, GEOM_ONE_CHILD)


class TestFrameConstruction(unittest.TestCase):
    def test_the_committed_fields_keep_their_positions(self):
        # title, width, top, bottom, children were positional in HEAD. New fields must come after them, not before.
        names = [f.name for f in dataclasses.fields(util.Frame)]
        self.assertEqual(names[:5], ["title", "width", "top", "bottom", "children"])

    def test_positional_construction_with_the_committed_arguments_still_works(self):
        frame = util.Frame("auth", 25, 0, 2, [])
        self.assertEqual((frame.title, frame.width, frame.top, frame.bottom), ("auth", 25, 0, 2))
        self.assertEqual(frame.children, [])


if __name__ == "__main__":
    unittest.main()
