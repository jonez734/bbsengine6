"""inputstring draws its prompt from the cursor where it is, not from an absolute {curpos} to a queried row.

A field placed by a frame's relative moves is already where the caller left the cursor. An absolute move to a row taken
from the cursor query lands on the wrong row when the reply is stale or missing, which is what homes the prompt.
"""

import importlib
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")


class TestNoAbsoluteStart(unittest.TestCase):
    def test_the_prompt_is_not_drawn_at_an_absolute_position(self):
        out = []

        def fake(text="", *a, **k):
            out.append(str(text))

        with patch.object(ist, "echo", side_effect=fake), \
             patch.object(ist, "get_cursor_position", side_effect=TimeoutError("no reply")), \
             patch.object(ist, "input_origin", return_value=(2, 2, 20)):
            ist._start_field_here("moniker: ", 1, 1, 20)
        self.assertFalse(any("{curpos:" in t for t in out), f"absolute curpos in {out}")


if __name__ == "__main__":
    unittest.main()
