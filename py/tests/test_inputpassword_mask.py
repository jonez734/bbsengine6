"""inputpassword masks by default with nothing: a typed password is not shown, not even as X characters."""

import unittest
from unittest.mock import patch

from bbsengine6 import util


class TestInputPasswordMask(unittest.TestCase):
    def test_the_default_mask_is_empty(self):
        with patch.object(util.io, "inputstring", return_value="pw") as inp:
            util.inputpassword("password: ")
        self.assertEqual(inp.call_args.kwargs["mask"], "")

    def test_a_caller_can_still_choose_a_mask_character(self):
        with patch.object(util.io, "inputstring", return_value="pw") as inp:
            util.inputpassword("password: ", mask="*")
        self.assertEqual(inp.call_args.kwargs["mask"], "*")


if __name__ == "__main__":
    unittest.main()
