"""draw_box leaves the terminal in its normal character set: the box uses the line-drawing set (acs), and the
last thing it prints resets it with {f6}. Without the reset the rest of the screen is drawn in the line-drawing set."""

import unittest
from unittest.mock import patch

from bbsengine6 import util


class TestDrawBoxResetsTheCharset(unittest.TestCase):
    def _printed(self, *args, **kwargs):
        with patch.object(util.io, "echo") as echo:
            util.draw_box(*args, **kwargs)
        return [str(c.args[0]) if c.args else "" for c in echo.call_args_list], echo.call_args_list

    def test_a_titled_box_ends_with_the_charset_reset(self):
        texts, calls = self._printed("zoid6 auth", 25, 1)
        self.assertEqual(texts[-1], "{f6}", "the box's bottom edge is followed by the reset")
        self.assertIs(calls[-1].kwargs.get("end"), "", "the reset follows the bottom edge on the same line")

    def test_an_untitled_box_ends_with_the_charset_reset(self):
        texts, _ = self._printed("", 10, 1)
        self.assertEqual(texts[-1], "{f6}")

    def test_the_cursor_is_still_left_on_the_bottom_edge(self):
        # Callers move the cursor up from the bottom edge; the reset must not add a newline that would break that.
        _, calls = self._printed("x", 10, 1)
        bottom = [c for c in calls if "{acs:llcorner}" in str(c.args[0])][0]
        self.assertEqual(bottom.kwargs.get("end"), "")


if __name__ == "__main__":
    unittest.main()
