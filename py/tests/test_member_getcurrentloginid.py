"""member.getcurrentloginid returns the member's OS login (osuser), falling back to the process
login name when no member row or no osuser matches."""

import types
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import member as libmember
from bbsengine6.member import lib as memlib


class _Cur:
    def __init__(self, row, rowcount):
        self._row = row
        self.rowcount = rowcount

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **k):
        pass

    def fetchone(self):
        return self._row


def _conn(row, rowcount):
    c = MagicMock()
    c.cursor.return_value = _Cur(row, rowcount)
    return c


@pytest.fixture(autouse=True)
def _clear_cache():
    memlib._threadlocal.loginid = None
    yield
    memlib._threadlocal.loginid = None


@pytest.mark.unit
def test_returns_the_members_osuser():
    args = types.SimpleNamespace()
    with patch.object(memlib.util, "getcurrentloginid", return_value="jam"), \
         patch.object(memlib.database, "cursor", side_effect=lambda c: c.cursor()):
        out = memlib.getcurrentloginid(args, conn=_conn({"osuser": "jam_os"}, 1))
    assert out == "jam_os"


@pytest.mark.unit
def test_falls_back_to_the_process_login_when_no_member_row():
    args = types.SimpleNamespace()
    with patch.object(memlib.util, "getcurrentloginid", return_value="jam"), \
         patch.object(memlib.database, "cursor", side_effect=lambda c: c.cursor()):
        out = memlib.getcurrentloginid(args, conn=_conn(None, 0))
    assert out == "jam"


@pytest.mark.unit
def test_falls_back_when_the_member_has_no_osuser():
    args = types.SimpleNamespace()
    with patch.object(memlib.util, "getcurrentloginid", return_value="jam"), \
         patch.object(memlib.database, "cursor", side_effect=lambda c: c.cursor()):
        out = memlib.getcurrentloginid(args, conn=_conn({"osuser": None}, 1))
    assert out == "jam"


@pytest.mark.unit
def test_no_process_login_returns_none():
    args = types.SimpleNamespace()
    with patch.object(memlib.util, "getcurrentloginid", return_value=None):
        assert memlib.getcurrentloginid(args, conn=MagicMock()) is None


@pytest.mark.unit
def test_is_exported_from_the_member_package():
    assert libmember.getcurrentloginid is memlib.getcurrentloginid
