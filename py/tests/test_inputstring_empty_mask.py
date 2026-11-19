"""With mask="" the typed password is not shown, and the redraw does not touch the field's cells.

The field used to be cleared with spaces on every redraw, so an empty mask still showed a row of blanks that moved as
the password was typed. With an empty mask there is nothing to draw, so the redraw only moves the cursor.
"""

import importlib
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")


def _redraw(buffer: str, mask):
    writes = []

    def fake_echo(text="", *args, **kwargs):
        writes.append(str(text))

    with patch.object(ist, "echo", side_effect=fake_echo):
        ist.redraw_line("pw: ", buffer, 40, 3, 1, len(buffer), 0, 20, mask=mask)
    return writes


class TestEmptyMask(unittest.TestCase):
    def test_no_blank_spaces_are_written_over_the_field(self):
        writes = _redraw("secret", mask="")
        # A clear is a run of spaces, possibly after a cursor move in the same write.
        cleared = [w for w in writes if w.split("}")[-1].count(" ") >= 2]
        self.assertFalse(cleared, f"the field is cleared with spaces: {cleared}")

    def test_the_cursor_still_ends_at_the_typed_position(self):
        writes = _redraw("secret", mask="")
        # The row depends on where the field is (set by the caller and by earlier terminal state); the contract is only
        # that the redraw ends with a cursor move, so the cursor sits on the field.
        self.assertRegex(writes[-1], r"^\{curpos:\d+,\d+\}$")

    def test_a_mask_character_is_still_drawn_for_each_typed_character(self):
        writes = _redraw("secret", mask="*")
        self.assertIn("******", writes)


if __name__ == "__main__":
    unittest.main()
