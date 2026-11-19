"""One mask rule for the field (_field_text), and inputpassword's mask contract.

mask None shows the typed text (accessibility); "" shows nothing; a character shows one per key. inputpassword
rejects anything else, so a password is never shown by accident.
"""

import importlib
import unittest
from unittest.mock import patch

ist = importlib.import_module("bbsengine6.io.inputstring")
util = importlib.import_module("bbsengine6.util")


class TestFieldText(unittest.TestCase):
    def test_none_shows_the_typed_text(self):
        self.assertEqual(ist._field_text(None, "abc"), "abc")

    def test_empty_mask_shows_nothing(self):
        self.assertIsNone(ist._field_text("", "abc"))

    def test_a_character_mask_repeats_per_typed_character(self):
        self.assertEqual(ist._field_text("*", "abc"), "***")


class TestInputpasswordMask(unittest.TestCase):
    def _call(self, **kwargs):
        with patch.object(util.io, "inputstring", return_value="x") as ins:
            util.inputpassword("password: ", **kwargs)
        return ins.call_args.kwargs["mask"]

    def test_default_mask_is_empty(self):
        self.assertEqual(self._call(), "")

    def test_none_is_allowed_for_accessibility(self):
        self.assertIsNone(self._call(mask=None))

    def test_one_character_is_allowed(self):
        self.assertEqual(self._call(mask="*"), "*")

    def test_a_longer_mask_is_rejected(self):
        with self.assertRaises(ValueError):
            util.inputpassword("password: ", mask="XX")

    def test_mask_must_be_keyword(self):
        with patch.object(util.io, "inputstring", return_value="x"):
            with self.assertRaises(TypeError):
                util.inputpassword("password: ", "*")


if __name__ == "__main__":
    unittest.main()
