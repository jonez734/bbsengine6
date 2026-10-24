"""Approval provisions the psql login role too, not only the data role.

Approval used to create m_<moniker> and print a pg_ident.conf instruction, so an approved
member had no login role and could not connect. After approval the sysop is asked for the
OS username (default: the loginid), and the login role is created and granted the data
role, with the same prompts as the member console's [O] option.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import memberapproval

M = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y"}


def _process(bools, osuser="lo_test", ok=True):
    """Run the per-member decision with scripted yes/no answers."""
    conn = MagicMock()
    answers = iter(bools)
    with patch.object(memberapproval.member, "getbymoniker", return_value=M), \
         patch.object(memberapproval.member, "checkflag", return_value=True), \
         patch.object(memberapproval, "_set_email_verified"), \
         patch.object(memberapproval, "_approve_member", return_value=True) as appr, \
         patch.object(memberapproval, "_disapprove_member", return_value=True) as dis, \
         patch.object(memberapproval.pgrole, "ensure_login_role", return_value="m_lo_test") as elr, \
         patch.object(memberapproval.io, "inputboolean", side_effect=lambda *a, **k: next(answers)), \
         patch.object(memberapproval.io, "echo"), \
         patch.object(memberapproval.io, "inputstring", return_value=osuser), \
         patch.object(memberapproval.util, "hr"), \
         patch.object(memberapproval.console_member, "_ask_os_login_menu_full",
                      return_value=(osuser if ok else None, ok, None, False)) as ask, \
         patch.object(memberapproval.console_member, "_apply_os_login", return_value=True) as apply:
        memberapproval._process_member(object(), {"moniker": "lo_test"}, "sysop", conn=conn)
    return {"elr": elr, "ask": ask, "apply": apply, "appr": appr, "dis": dis}


@pytest.mark.unit
def test_approval_asks_for_the_os_username_and_writes_the_login_role():
    r = _process([True, True], osuser="lo_test")  # verified, approve
    r["appr"].assert_called_once()
    r["ask"].assert_called_once()
    r["apply"].assert_called_once()
    assert r["apply"].call_args.args[2] == "lo_test"


@pytest.mark.unit
def test_approval_blank_osuser_creates_no_login_role():
    r = _process([True, True], osuser=None, ok=False)
    r["apply"].assert_not_called()


@pytest.mark.unit
def test_disapproval_provisions_nothing():
    r = _process([True, False])  # verified, do not approve
    r["dis"].assert_called_once()
    r["elr"].assert_not_called()
    r["ask"].assert_not_called()
    r["apply"].assert_not_called()


@pytest.mark.unit
def test_approval_does_not_print_the_pg_ident_instruction():
    import inspect
    src = inspect.getsource(memberapproval)
    assert "bbbsmap" not in src
    assert "pg_ident" not in src


@pytest.mark.unit
def test_stored_osuser_is_looked_up_by_join_and_used_as_default():
    """An approved member whose engine.pgrole row already has an osuser keeps it as the default."""
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = {"osuser": "lo_os"}
    assert memberapproval._stored_osuser_for_moniker(conn, "lo_test") == "lo_os"
    sql = cur.execute.call_args.args[0]
    assert "engine.pgrole_member" in sql


@pytest.mark.unit
def test_new_member_with_no_pgrole_osuser_gets_none_as_stored():
    conn = MagicMock()
    cur = conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = None
    assert memberapproval._stored_osuser_for_moniker(conn, "lo_test") is None


@pytest.mark.unit
def test_process_member_passes_the_stored_osuser_as_the_default():
    r = None
    conn = MagicMock()
    with patch.object(memberapproval, "_stored_osuser_for_moniker", return_value="lo_os"), \
         patch.object(memberapproval.member, "getbymoniker", return_value=M), \
         patch.object(memberapproval.member, "checkflag", return_value=True), \
         patch.object(memberapproval, "_set_email_verified"), \
         patch.object(memberapproval, "_approve_member", return_value=True), \
         patch.object(memberapproval.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(memberapproval.io, "inputboolean", side_effect=[True, True]), \
         patch.object(memberapproval.io, "echo"), \
         patch.object(memberapproval.util, "hr"), \
         patch.object(memberapproval.console_member, "_ask_os_login_menu_full",
                      return_value=("lo_os", True, None, False)) as ask, \
         patch.object(memberapproval.console_member, "_apply_os_login", return_value=True):
        memberapproval._process_member(object(), {"moniker": "lo_test"}, "sysop", conn=conn)
    assert ask.call_args.kwargs.get("stored") == "lo_os"
