"""inputstring starts at the cursor the caller placed, not at row 1, column 1, when the terminal does not answer.

A frame places the field with {curpos}. If the cursor query gets no answer, the field used to fall back to (1, 1) and
redraw the prompt at the top of the screen. The fallback is the tracked cursor the caller left, not a constant.
"""

import importlib
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")
common = importlib.import_module("bbsengine6.io.common")


class TestStartsWhereTheCallerLeftTheCursor(unittest.TestCase):
    def test_with_no_answer_the_start_is_the_tracked_cursor(self):
        with patch.object(ist, "get_cursor_position", side_effect=TimeoutError("no reply")), \
             patch.object(common, "_get_terminal_state") as get_state:
            state = get_state.return_value
            state.cursor_row, state.cursor_col = 4, 2
            self.assertEqual(ist._cursor_origin_or_default(), (4, 2))

    def test_with_no_answer_and_no_tracked_cursor_the_start_is_row_1_column_1(self):
        with patch.object(ist, "get_cursor_position", side_effect=TimeoutError("no reply")), \
             patch.object(common, "_get_terminal_state") as get_state:
            state = get_state.return_value
            state.cursor_row, state.cursor_col = None, None
            self.assertEqual(ist._cursor_origin_or_default(), (1, 1))

    def test_a_real_answer_still_wins(self):
        with patch.object(ist, "get_cursor_position", return_value=(7, 3)):
            self.assertEqual(ist._cursor_origin_or_default(), (7, 3))


if __name__ == "__main__":
    unittest.main()
