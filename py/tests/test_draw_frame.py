"""draw_frame, extend_frame: a frame that grows a child box after it is drawn.

A frame is drawn once and returns its geometry (top row, bottom row, and each interior). extend_frame adds a child below
the frame's bottom edge: it overwrites that edge with a join (ltee/rtee) between save (decsc) and restore (decrc), then
draws the child under it. A child that does not fit on the screen scrolls the screen first, and the geometry moves with it.
"""

import unittest
from unittest.mock import patch

from bbsengine6 import util


def _capture(fn, *args, **kwargs):
    """Run ``fn`` with io.echo replaced; return (result, [(text, end), ...])."""
    out = []

    def fake_echo(text="", end="\n", **_):
        out.append((str(text), end))

    with patch.object(util.io, "echo", side_effect=fake_echo):
        result = fn(*args, **kwargs)
    return result, out


class TestDrawBoxIsUnchanged(unittest.TestCase):
    def test_a_titled_box_prints_exactly_what_it_printed_before(self):
        _, out = _capture(util.draw_box, "zoid6 auth", 25, 1)
        self.assertEqual(out[0][0], "{boxcolor}{ulcorner}{hline}{ltee} {promptcolor}zoid6 auth{boxcolor} {rtee}{hline:10}{urcorner}")
        self.assertEqual(out[1][0], "{acs:vline}" + " " * 25 + "{acs:vline}")
        self.assertEqual(out[2], ("{acs:llcorner}{acs:hline:25}{acs:lrcorner}", ""))
        self.assertEqual(out[3], ("{f6}", ""))


class TestDrawFrameGeometry(unittest.TestCase):
    def test_a_frame_with_no_children_reports_its_rows(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        self.assertEqual(frame.top, 0)
        self.assertEqual(frame.bottom, 2)  # top edge, one interior row, bottom edge
        self.assertEqual(frame.children, [])

    def test_a_frame_with_one_child_reports_the_child_interior(self):
        frame, _ = _capture(util.draw_frame, "auth", 25, children=[util.Child(title="moniker")])
        self.assertEqual(len(frame.children), 1)
        self.assertEqual(frame.children[0].column, 2)  # inside the left edge and one space in

    def test_stacked_children_are_placed_one_under_another(self):
        frame, _ = _capture(util.draw_frame, "auth", 25,
                            children=[util.Child(title="moniker"), util.Child(title="password")])
        self.assertGreater(frame.children[1].top, frame.children[0].bottom)

    def test_a_zero_gap_shares_the_line_between_stacked_children(self):
        frame, _ = _capture(util.draw_frame, "auth", 25,
                            children=[util.Child(title="a"), util.Child(title="b", gap=0)])
        self.assertEqual(frame.children[1].top, frame.children[0].bottom)


class TestExtendFrame(unittest.TestCase):
    def test_the_join_is_written_between_save_and_restore(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        _, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        texts = [t for t, _ in out]
        save = texts.index("{decsc}")
        restore = texts.index("{decrc}")
        join = [i for i, t in enumerate(texts) if "{acs:ltee}" in t and "{acs:rtee}" in t]
        self.assertTrue(join, "a join line is written")
        self.assertLess(save, join[0])
        self.assertLess(join[0], restore)

    def test_the_join_is_written_at_the_frame_bottom_row(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        bottom = frame.bottom
        _, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        texts = [t for t, _ in out]
        self.assertIn("{cha:1}", texts, "the join starts at column 1 of the bottom edge (relative, no absolute curpos)")

    def test_the_join_is_the_frame_width(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        _, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        join = [t for t, _ in out if "{acs:ltee}" in t and "{acs:rtee}" in t][0]
        self.assertIn("{acs:hline:25}", join)

    def test_the_child_is_drawn_below_the_old_bottom_edge(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        old_bottom = frame.bottom  # extend_frame updates the frame in place, so record the edge first
        extended, _ = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        self.assertGreater(extended.children[-1].top, old_bottom)

    def test_the_child_is_the_same_width_as_the_frame(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        extended, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        child_rows = [t for t, _ in out if t.startswith("{acs:vline}")]
        self.assertTrue(all(len(t) == len("{acs:vline}") + 25 + len("{acs:vline}") for t in child_rows))


class TestNearTheBottom(unittest.TestCase):
    def test_a_child_that_does_not_fit_scrolls_the_screen_and_the_join_still_lands(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        original_top = frame.top  # extend_frame updates the frame in place, so record the top first
        with patch.object(util, "_terminal_rows", return_value=4):
            extended, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        scrolls = [t for t, e in out if t == "" and e == "\n"]
        self.assertGreater(len(scrolls), 0, "the screen is scrolled to make room")
        # The screen scrolled up by the rows printed, so the frame's top moved up by the same amount. The bottom
        # then grows with the child, so only the top is checked against the scroll.
        self.assertEqual(extended.top, original_top - len(scrolls))

    def test_a_child_that_fits_does_not_scroll(self):
        frame, _ = _capture(util.draw_frame, "auth", 25)
        with patch.object(util, "_terminal_rows", return_value=40):
            _, out = _capture(util.extend_frame, frame, util.Child(title="password"), width=25)
        self.assertEqual([t for t, e in out if t == "" and e == "\n"], [])


if __name__ == "__main__":
    unittest.main()
