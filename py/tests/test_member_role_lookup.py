"""The request path resolves a member's role from engine.pgrole only.

as_member must never provision a database role. A member with no tracking row
is refused, and no CREATE ROLE or tracking-row insert runs on the request path.
Provisioning stays with ensure_login_role, which the approval and console flows call.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import member_role, pgrole


def test_lookup_returns_existing_role_without_provisioning():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"rolname": "jam"}
    with patch.object(pgrole, "_ensure_login_role") as ensure:
        assert pgrole.lookup_login_role(object(), "jam", conn=conn) == "jam"
    ensure.assert_not_called()


def test_lookup_returns_none_without_a_row():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = None
    with patch.object(pgrole, "_ensure_login_role") as ensure:
        assert pgrole.lookup_login_role(object(), "ghost", conn=conn) is None
    ensure.assert_not_called()


def test_as_member_refuses_when_no_row_and_never_provisions():
    @contextmanager
    def never(*a, **k):
        raise AssertionError("switch must not run")
        yield  # pragma: no cover

    with patch.object(member_role.pgrole, "lookup_login_role", return_value=None), \
         patch.object(member_role.pgrole, "ensure_login_role") as ensure:
        with pytest.raises(PermissionError, match="no database role"):
            with member_role.as_member(object(), "ghost", conn=MagicMock()):
                pass
    ensure.assert_not_called()


def test_as_member_uses_lookup_not_provisioning():
    @contextmanager
    def fine(*a, **k):
        yield

    with patch.object(member_role.pgrole, "lookup_login_role", return_value="jam") as look, \
         patch.object(member_role.pgrole, "ensure_login_role") as ensure, \
         patch.object(member_role.database, "switch_role", side_effect=fine):
        with member_role.as_member(object(), "jam", conn=MagicMock()):
            pass
    look.assert_called_once()
    ensure.assert_not_called()
