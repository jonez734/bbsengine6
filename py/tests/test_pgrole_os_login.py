"""The OS-user login role that ident maps to a member's m_<moniker> role.

ident (no pg_ident map) logs a connection in as the role named like the OS user, so the
shell connects as <osuser>. The login role is created NOINHERIT: it holds no privileges
of its own and acts only through SET ROLE m_<moniker>, which needs membership in it.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import pgrole


def _conn_with_cursor():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    return conn, cur


@pytest.mark.unit
def test_creates_noinherit_login_role_when_missing():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True) as cr:
        ok = pgrole.ensure_os_login_role(object(), "lo_test", "m_lo_test", conn=conn)
    assert ok is True
    cr.assert_called_once()
    assert cr.call_args.args[1] == "lo_test"
    assert cr.call_args.kwargs.get("login") is True
    assert cr.call_args.kwargs.get("inherit") is False


@pytest.mark.unit
def test_does_not_recreate_an_existing_login_role():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "createrol") as cr:
        ok = pgrole.ensure_os_login_role(object(), "lo_test", "m_lo_test", conn=conn)
    assert ok is True
    cr.assert_not_called()


@pytest.mark.unit
def test_grants_the_member_role_to_the_login_role():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "createrol"):
        pgrole.ensure_os_login_role(object(), "lo_test", "m_lo_test", conn=conn)
    # Render the composed SQL without a live connection: Identifier quoting is pure.
    rendered = [
        c.args[0].as_string(None) if hasattr(c.args[0], "as_string") else str(c.args[0])
        for c in cur.execute.call_args_list
    ]
    assert any(s == 'GRANT "m_lo_test" TO "lo_test"' for s in rendered), rendered


@pytest.mark.unit
def test_refuses_an_osuser_that_is_not_a_plain_name():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "rolexists") as rex, \
         patch.object(pgrole.database, "createrol") as cr:
        ok = pgrole.ensure_os_login_role(object(), "lo test; drop", "m_lo_test", conn=conn)
    assert ok is False
    rex.assert_not_called()
    cr.assert_not_called()


@pytest.mark.unit
def test_refuses_to_use_the_member_role_as_the_login_role():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "createrol") as cr:
        ok = pgrole.ensure_os_login_role(object(), "m_lo_test", "m_lo_test", conn=conn)
    assert ok is False
    cr.assert_not_called()


@pytest.mark.unit
def test_returns_false_when_creation_fails():
    conn, cur = _conn_with_cursor()
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=False):
        ok = pgrole.ensure_os_login_role(object(), "lo_test", "m_lo_test", conn=conn)
    assert ok is False
