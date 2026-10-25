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


class TestSysopCheckKeepsLoginRole(unittest.TestCase):
    """The sysop check runs as bed's login role, so it must not inherit the member role.

    A plain database.connect() takes the process-wide role. For a bound member that issues
    SET LOCAL ROLE <member>, which bed's login role cannot do, so login fails after the token
    is minted.
    """

    def test_checkflag_connects_with_set_role_false(self):
        from bbsengine6 import database
        from unittest.mock import MagicMock, patch

        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = {"checkmemberflag": True}
        cur.rowcount = 1
        conn.cursor.return_value.__enter__.return_value = cur
        conn.__enter__.return_value = conn
        pool = MagicMock()

        with patch.object(database, "connect", return_value=conn) as connect, \
                patch.object(database, "cursor", return_value=cur):
            member.checkflag(MagicMock(), "sysop", moniker="jam", pool=pool)

        self.assertIs(connect.call_args.kwargs.get("set_role"), False)

    def test_has_sysop_role_connects_with_set_role_false(self):
        from bbsengine6 import database
        from unittest.mock import MagicMock, patch

        conn = MagicMock()
        cur = MagicMock()
        cur.fetchone.return_value = None
        conn.cursor.return_value.__enter__.return_value = cur
        conn.__enter__.return_value = conn
        pool = MagicMock()

        with patch.object(database, "connect", return_value=conn) as connect, \
                patch.object(database, "cursor", return_value=cur):
            member._has_sysop_role(MagicMock(), "jam", pool=pool)

        self.assertIs(connect.call_args.kwargs.get("set_role"), False)
