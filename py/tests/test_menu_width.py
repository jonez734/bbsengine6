"""Menu items and the menu frame use the terminal width, clamped by terminal.width() (120 by default), with no separate
100-column cap in the menu. A wide terminal gets wide items; a narrow one gets its own width."""

import unittest
from unittest.mock import patch

from bbsengine6 import menu as bmenu


class TestMenuWidth(unittest.TestCase):
    def test_an_item_takes_the_terminal_width_up_to_the_120_column_clamp(self):
        with patch.object(bmenu.io.terminal, "width", return_value=120):
            item = bmenu.Item("A", "alpha", None)
        self.assertEqual(item.width, 120)

    def test_an_item_on_a_wide_terminal_is_not_capped_at_100(self):
        with patch.object(bmenu.io.terminal, "width", return_value=110):
            item = bmenu.Item("A", "alpha", None)
        self.assertEqual(item.width, 110)

    def test_an_item_on_a_narrow_terminal_keeps_its_width(self):
        with patch.object(bmenu.io.terminal, "width", return_value=80):
            item = bmenu.Item("A", "alpha", None)
        self.assertEqual(item.width, 80)


if __name__ == "__main__":
    unittest.main()
