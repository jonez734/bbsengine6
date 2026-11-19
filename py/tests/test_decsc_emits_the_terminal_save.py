"""{decsc} and {decrc} send the terminal's save and restore cursor (ESC 7 and ESC 8). They do not query the cursor.

The handler used to ask the terminal where the cursor is (a DSR round trip) and keep the answer on a software stack. A
program that writes a join between save and restore, with no reply coming back, then timed out. Save and restore are VT10x
primitives, so the handler now emits them directly.
"""

import unittest
from unittest.mock import patch

import importlib

echo = importlib.import_module("bbsengine6.io.echo")


class TestSaveRestoreEmitsEscapes(unittest.TestCase):
    def test_decsc_writes_esc_7_and_does_not_query_the_cursor(self):
        with patch.object(echo, "get_cursor_position", side_effect=AssertionError("must not query")) as query:
            written = echo._decsc_bytes()
            token = echo.Token(kind="WHITESPACE", repeat=1, text="{decsc}")
            echo._handle_decsc(token)
        query.assert_not_called()
        self.assertEqual(written, "\x1b7")

    def test_decrc_writes_esc_8(self):
        self.assertEqual(echo._decrc_bytes(), "\x1b8")


if __name__ == "__main__":
    unittest.main()
