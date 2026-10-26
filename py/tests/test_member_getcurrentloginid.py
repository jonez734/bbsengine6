"""member.getcurrentloginid returns the current OS login, as queried from the operating system.

It delegates to util.getcurrentloginid (os.getlogin, then the login environment variables). It
does not read the database; a member's stored OS login (engine.pgrole.osuser) is a separate value.
"""

import types
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import member as libmember
from bbsengine6.member import lib as memlib


@pytest.mark.unit
def test_returns_the_os_login_from_util():
    with patch.object(memlib.util, "getcurrentloginid", return_value="jam") as os_login:
        assert memlib.getcurrentloginid(types.SimpleNamespace()) == "jam"
    os_login.assert_called_once()


@pytest.mark.unit
def test_does_not_query_the_database():
    conn = MagicMock()
    with patch.object(memlib.util, "getcurrentloginid", return_value="jam"):
        memlib.getcurrentloginid(types.SimpleNamespace(), conn=conn)
    conn.cursor.assert_not_called()


@pytest.mark.unit
def test_returns_none_when_the_os_gives_no_login():
    with patch.object(memlib.util, "getcurrentloginid", return_value=None):
        assert memlib.getcurrentloginid(types.SimpleNamespace()) is None


@pytest.mark.unit
def test_is_exported_from_the_member_package():
    assert libmember.getcurrentloginid is memlib.getcurrentloginid
