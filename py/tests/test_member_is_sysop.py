"""member.is_sysop(): a member is a sysop if the flag is set OR the member's role is in sysop.

The flag (engine.map_member_flag 'SYSOP') and the Postgres role membership
(pg_auth_members, the 'sysop' role or the member's m_<moniker> data role) are two
sources of the same fact. Either one makes the member a sysop.
"""

import unittest
from unittest.mock import MagicMock, patch

from bbsengine6.member import lib as member


class TestMemberIsSysop(unittest.TestCase):
    def test_flag_true_no_role_is_sysop(self):
        with patch.object(member, "issysop", return_value=True), \
                patch.object(member, "_has_sysop_role", return_value=False):
            self.assertTrue(member.is_sysop(MagicMock(), moniker="jam", pool=MagicMock()))

    def test_role_only_is_sysop(self):
        with patch.object(member, "issysop", return_value=False), \
                patch.object(member, "_has_sysop_role", return_value=True):
            self.assertTrue(member.is_sysop(MagicMock(), moniker="jam", pool=MagicMock()))

    def test_neither_is_not_sysop(self):
        with patch.object(member, "issysop", return_value=False), \
                patch.object(member, "_has_sysop_role", return_value=False):
            self.assertFalse(member.is_sysop(MagicMock(), moniker="bob", pool=MagicMock()))

    def test_flag_none_falls_back_to_role(self):
        with patch.object(member, "issysop", return_value=None), \
                patch.object(member, "_has_sysop_role", return_value=True):
            self.assertTrue(member.is_sysop(MagicMock(), moniker="jam", pool=MagicMock()))


if __name__ == "__main__":
    unittest.main()
