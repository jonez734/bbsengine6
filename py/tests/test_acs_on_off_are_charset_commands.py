"""{acs:on} and {acs:off} switch the character set. They must not print a '?'.

{acs:off} fell through to the ACS character path, which looked up "off" in the glyph map,
missed, and printed '?' under DEC graphics. The field's charset reset therefore showed as a
'?' before the moniker prompt.
"""

import importlib
import io as pyio
import unittest
from unittest.mock import patch

E = importlib.import_module("bbsengine6.io.echo")
common = importlib.import_module("bbsengine6.io.common")


def _render(markup):
    out = pyio.StringIO()
    common.set_output_stream(out)
    st = common._get_terminal_state()
    st.acs = False
    with patch.object(E.terminal, "lines", return_value=8), patch.object(E.terminal, "columns", return_value=80):
        E.echo(markup, end="")
    return out.getvalue()


class TestAcsOnOff(unittest.TestCase):
    def test_acs_off_emits_only_the_charset_reset(self):
        self.assertEqual(_render("{acs:off}"), "")  # already off: nothing to write

    def test_acs_off_after_on_writes_esc_b_and_no_question_mark(self):
        out = _render("{acs:on}{acs:off}")
        self.assertIn("\x1b(B", out)
        self.assertNotIn("?", out)

    def test_acs_on_writes_esc_0_and_no_question_mark(self):
        out = _render("{acs:on}")
        self.assertEqual(out, "\x1b(0")

    def test_plain_text_is_written_with_the_charset_off_and_no_question_mark(self):
        # Ordinary text leaves the DEC charset first (the echo layer does this for every word),
        # so a reset followed by text shows the text, not a '?'.
        out = _render("{acs:on}x{acs:off}abc")
        self.assertNotIn("?", out)
        self.assertEqual(out, "\x1b(0\x1b(Bxabc")


if __name__ == "__main__":
    unittest.main()
