"""{decsc} writes the terminal's save (ESC 7) to the output, the same as {decrc} writes ESC 8.

The save handler set token.text but never yielded the token, so echo("{decsc}") wrote nothing. Every restore still
went out, so the terminal restored a stale or unset position and a frame's join landed on the wrong row.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

from bbsengine6.io import common

E = importlib.import_module("bbsengine6.io.echo")


class TestDecscWritesTheSave(unittest.TestCase):
    def _echo(self, markup):
        out = pyio.StringIO()
        common.set_output_stream(out)
        with patch.object(E.terminal, "lines", return_value=24), patch.object(E.terminal, "columns", return_value=80):
            E.echo(markup, end="")
        return out.getvalue()

    def test_decsc_writes_esc_7(self):
        self.assertEqual(self._echo("{decsc}"), "\x1b7")

    def test_decrc_writes_esc_8(self):
        self.assertEqual(self._echo("{decrc}"), "\x1b8")

    def test_each_save_has_a_matching_restore_in_the_output(self):
        out = self._echo("{decsc}x{decrc}")
        self.assertEqual(out.count("\x1b7"), 1)
        self.assertEqual(out.count("\x1b8"), 1)
        self.assertLess(out.index("\x1b7"), out.index("\x1b8"))


if __name__ == "__main__":
    unittest.main()
