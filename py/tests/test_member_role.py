"""as_member runs member work as the member's role and fails closed."""

import types
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import member_role

_ARGS = types.SimpleNamespace(debug=False)


@contextmanager
def _fake_switch(*a, **k):
    yield


def test_enters_members_role_for_the_block():
    conn = MagicMock()
    with patch.object(member_role.pgrole, "lookup_login_role", return_value="jam") as ens, \
         patch.object(member_role.database, "switch_role", side_effect=_fake_switch) as sw:
        with member_role.as_member(object(), "jam", conn=conn):
            pass
    ens.assert_called_once()
    assert sw.call_args.args[1] == "jam"


def test_refuses_when_member_has_no_role():
    with patch.object(member_role.pgrole, "lookup_login_role", return_value=None):
        with pytest.raises(PermissionError, match="no database role"):
            with member_role.as_member(_ARGS, "ghost", conn=MagicMock()):
                pass


def test_refuses_when_switch_is_denied():
    def denied(*a, **k):
        raise ValueError("switch_role: role 'jam' does not exist")

    with patch.object(member_role.pgrole, "ensure_login_role", return_value="jam"), \
         patch.object(member_role.database, "switch_role", side_effect=denied):
        with pytest.raises(PermissionError, match="cannot run as"):
            with member_role.as_member(_ARGS, "jam", conn=MagicMock()):
                pass


def test_block_does_not_run_when_refused():
    ran = []
    with patch.object(member_role.pgrole, "lookup_login_role", return_value=None):
        with pytest.raises(PermissionError):
            with member_role.as_member(_ARGS, "ghost", conn=MagicMock()):
                ran.append(1)
    assert ran == []


def test_requires_a_connection():
    with pytest.raises(ValueError):
        with member_role.as_member(object(), "jam"):
            pass
