"""Changing a member's osuser: remove the old login role's grant (after a prompt), and
keep engine.pgrole in step with the new osuser. Writes happen when the menu exits."""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import pgrole
from bbsengine6.console import member as console_member


def _sql(cur):
    out = []
    for c in cur.execute.call_args_list:
        a = c.args[0]
        out.append(a.as_string(None) if hasattr(a, "as_string") else str(a))
    return out


@pytest.mark.unit
def test_remove_revokes_the_data_role_from_the_old_login_role():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False, "rolcanlogin": True}):
        ok = pgrole.remove_os_login_role(object(), "lo_old", "m_lo_test", conn=conn, drop_role=False)
    assert ok is True
    assert 'REVOKE "m_lo_test" FROM "lo_old"' in _sql(cur)
    assert not any(s.startswith("DROP ROLE") for s in _sql(cur))


@pytest.mark.unit
def test_remove_drops_the_old_login_role_only_when_asked():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    with patch.object(pgrole.database, "rolexists", return_value=True), \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False, "rolcanlogin": True}):
        pgrole.remove_os_login_role(object(), "lo_old", "m_lo_test", conn=conn, drop_role=True)
    assert 'DROP ROLE "lo_old"' in _sql(cur)


@pytest.mark.unit
def test_remove_refuses_superusers_and_jam():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    for name, privs in (("jam", {"rolsuper": False}), ("su_role", {"rolsuper": True})):
        with patch.object(pgrole.database, "rolexists", return_value=True), \
             patch.object(pgrole.database, "get_role_privs", return_value=privs):
            ok = pgrole.remove_os_login_role(object(), name, "m_lo_test", conn=conn, drop_role=True)
        assert ok is False, name
    assert not any(s.startswith(("REVOKE", "DROP")) for s in _sql(cur))


@pytest.mark.unit
def test_remove_of_a_missing_role_is_a_no_op_success():
    conn = MagicMock()
    with patch.object(pgrole.database, "rolexists", return_value=False):
        assert pgrole.remove_os_login_role(object(), "ghost", "m_lo_test", conn=conn, drop_role=True) is True


@pytest.mark.unit
def test_changing_osuser_asks_whether_to_remove_the_old_one():
    """[O] with a different name than the stored osuser asks about the old one."""
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_old"}
    with patch.object(console_member.io, "inputstring", return_value="lo_new"), \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.io, "inputboolean", return_value=False) as ask, \
         patch("bbsengine6.console.member.io.echo"):
        osuser, ok, old, remove = console_member._ask_os_login_menu_full(object(), "lo_test", conn=conn, stored="lo_old")
    assert osuser == "lo_new" and ok is True
    assert old == "lo_old"
    assert remove is False
    assert any("lo_old" in str(c.args[0]) for c in ask.call_args_list)


@pytest.mark.unit
def test_unchanged_osuser_asks_nothing_about_removal():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_old"}
    with patch.object(console_member.io, "inputstring", return_value="lo_old"), \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.io, "inputboolean") as ask, \
         patch("bbsengine6.console.member.io.echo"):
        osuser, ok, old, remove = console_member._ask_os_login_menu_full(object(), "lo_test", conn=conn, stored="lo_old")
    assert osuser == "lo_old" and ok is True
    assert old is None and remove is False
    ask.assert_not_called()


@pytest.mark.unit
def test_apply_removes_the_old_login_role_and_updates_the_tracking_row():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    with patch.object(console_member.pgrole, "ensure_os_login_role", return_value=True), \
         patch.object(console_member.pgrole, "remove_os_login_role", return_value=True) as rm, \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member._apply_os_login(object(), "m_lo_test", "lo_new",
                                            conn=conn, old_osuser="lo_old", remove_old=True)
    assert ok is True
    rm.assert_called_once()
    assert rm.call_args.args[1] == "lo_old"
    assert any("UPDATE engine.pgrole SET osuser" in s for s in _sql(cur))


@pytest.mark.unit
def test_apply_keeps_the_old_login_role_when_not_asked_to_remove():
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_os_login_role", return_value=True), \
         patch.object(console_member.pgrole, "remove_os_login_role") as rm, \
         patch("bbsengine6.console.member.io.echo"):
        console_member._apply_os_login(object(), "m_lo_test", "lo_new",
                                       conn=conn, old_osuser="lo_old", remove_old=False)
    rm.assert_not_called()
