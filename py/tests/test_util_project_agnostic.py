"""util is project agnostic: its ltree helpers do only the generic conversion, with no project's root rule.

A PostgreSQL ltree is a dot-separated label path. Which label is a project's root is that project's convention, so
ltree_to_path keeps every label. Projects that drop a root do it themselves.
"""

import unittest

from bbsengine6 import util


class TestLtreeIsGeneric(unittest.TestCase):
    def test_ltree_to_path_keeps_every_label(self):
        self.assertEqual(util.ltree_to_path("top.users.admin"), "top/users/admin")

    def test_ltree_to_path_does_not_drop_a_leading_top(self):
        self.assertEqual(util.ltree_to_path("users.admin"), "users/admin")

    def test_pathToLtree_and_ltree_to_path_are_inverse_for_plain_paths(self):
        self.assertEqual(util.ltree_to_path(util.pathToLtree("software/python")), "software/python")

    def test_chop_last_element_removes_one_label(self):
        self.assertEqual(util.chop_last_element("top.users.admin"), "top.users")


if __name__ == "__main__":
    unittest.main()
