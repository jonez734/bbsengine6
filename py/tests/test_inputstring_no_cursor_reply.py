"""inputstring starts a field even when the terminal does not answer the cursor query.

It asks the terminal where the cursor is, and the code already falls back to row 1, column 1 when the answer is not a
position. A terminal that never answers used to raise TimeoutError out of the query, before the fallback could run, so
the field never started (a pipe, a dumb terminal, or a stream with no reply).
"""

import importlib
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")


class TestNoCursorReply(unittest.TestCase):
    def test_a_timeout_on_the_cursor_query_falls_back_instead_of_raising(self):
        with patch.object(ist, "get_cursor_position", side_effect=TimeoutError("DSR response not received")):
            pos = ist._cursor_origin_or_default()
        self.assertEqual(pos, (1, 1))

    def test_a_real_answer_is_used_as_the_start_position(self):
        with patch.object(ist, "get_cursor_position", return_value=(7, 3)):
            pos = ist._cursor_origin_or_default()
        self.assertEqual(pos, (7, 3))


if __name__ == "__main__":
    unittest.main()
