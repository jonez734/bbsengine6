"""A password typed with mask="" writes no typed character and no space: only cursor moves.

The live edit loop redraws the field after each key. With an empty mask that redraw must write nothing for the
typed text. This drives inputstring with fake keys and checks every write made after the prompt.
"""

import importlib
import re
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")

_CONTROL = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b[()][0-9A-Za-z]|\x1b[78]|\{[^}]*\}")


def _writes_for_keys(keys, mask):
    writes = []
    queue = list(keys)

    def fake_echo(text="", *args, **kwargs):
        writes.append(str(text))

    def fake_getch(*args, **kwargs):
        return queue.pop(0) if queue else "KEY_ENTER"

    with patch.object(ist, "echo", side_effect=fake_echo), patch.object(ist, "getch", side_effect=fake_getch), \
         patch.object(ist, "get_cursor_position", side_effect=TimeoutError("no reply")), \
         patch.object(ist, "input_origin", return_value=(5, 11, 20)), \
         patch.object(ist, "begin_raw_session", lambda *a, **k: None), \
         patch.object(ist, "end_raw_session", lambda *a, **k: None):
        result = ist.inputstring("password: ", "", mask=mask, bottombar=False, max_width=20)
    return result, writes


class TestPasswordWritesNoGlyphs(unittest.TestCase):
    def test_typed_keys_write_no_character_or_space_after_the_prompt(self):
        result, writes = _writes_for_keys(list("abc"), mask="")
        self.assertEqual(result, "abc")
        after_prompt = writes[writes.index(next(w for w in writes if "password" in w)) + 1:]
        visible = [w for w in after_prompt if _CONTROL.sub("", w).strip(" ") or " " in _CONTROL.sub("", w)]
        self.assertEqual(visible, [], f"a password key was written as text or a space: {visible}")


if __name__ == "__main__":
    unittest.main()


class TestEmptyMaskLeavesTheFieldUnchanged(unittest.TestCase):
    """An empty mask changes nothing on screen: no text, no clear, and no cursor move while typing."""

    def test_no_output_at_all_after_the_prompt_for_typed_keys(self):
        result, writes = _writes_for_keys(list("abc"), mask="")
        self.assertEqual(result, "abc")
        prompt_at = next(i for i, w in enumerate(writes) if "password" in w)
        after = [w for w in writes[prompt_at + 1:] if w not in ("{f6}",)]
        # Only the Enter that ends the line is allowed to write anything after the prompt.
        moves = [w for w in after if w.startswith("{curpos:")]
        self.assertEqual(moves, [], f"the cursor moved while typing with mask='': {moves}")
