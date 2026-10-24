"""configurerole provisions through the canonical pgrole path.

The console used to CREATE ROLE <loginid> and never wrote engine.pgrole, so members
created in the console had no tracking row and no 'member' grant, and the request path
(member_role.as_member) refused them. configurerole must now go through
pgrole.ensure_login_role (m_<moniker>, 'member' grant, tracking row) and sync groups
through pgrole.sync_groups.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import member as console_member


def _args():
    return SimpleNamespace(debug=False)


@pytest.mark.unit
def test_configurerole_calls_ensure_login_role_with_the_moniker():
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test") as ens, \
         patch.object(console_member.pgrole, "sync_groups", return_value=True), \
         patch.object(console_member.database, "rolexists") as rex, \
         patch.object(console_member.database, "createrol") as cr, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is True
    ens.assert_called_once()
    assert ens.call_args.args[1] == "lo_test"
    # The existence check is on the m_ role name, not the loginid.
    rex.assert_called_once()
    assert rex.call_args.args[1] == "m_lo_test"
    cr.assert_not_called()


@pytest.mark.unit
def test_configurerole_never_creates_a_bare_loginid_role():
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "sync_groups", return_value=True), \
         patch.object(console_member.database, "createrol") as cr, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    cr.assert_not_called()


@pytest.mark.unit
def test_configurerole_uses_the_rolname_returned_by_pgrole():
    """Privileges must target the m_<moniker> role, not the loginid."""
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs") as mp, \
         patch.object(console_member.database, "manage_secondary_role") as ms, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        console_member.configurerole(_args(), "lo_test", sysop=True, conn=conn, moniker="lo_test")
    assert mp.call_args_list and all(c.args[1] == "m_lo_test" for c in mp.call_args_list)
    assert ms.call_args_list and all(c.args[1] == "m_lo_test" for c in ms.call_args_list)


@pytest.mark.unit
def test_configurerole_prompts_before_creating_a_missing_role():
    """A new psql role is a database change, so the sysop is asked first (as before)."""
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=False), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test") as ens, \
         patch.object(console_member.io, "inputboolean", return_value=True) as ask, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is True
    ask.assert_called_once()
    assert "lo_test" in ask.call_args.args[0]
    ens.assert_called_once()


@pytest.mark.unit
def test_configurerole_declined_prompt_creates_nothing():
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=False), \
         patch.object(console_member.pgrole, "ensure_login_role") as ens, \
         patch.object(console_member.database, "manage_role_privs") as mp, \
         patch.object(console_member.database, "manage_secondary_role") as ms, \
         patch.object(console_member.io, "inputboolean", return_value=False), \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo") as echo:
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is False
    ens.assert_not_called()
    mp.assert_not_called()
    ms.assert_not_called()
    assert any("not created" in str(c.args[0]) for c in echo.call_args_list)


@pytest.mark.unit
def test_configurerole_existing_role_does_not_prompt():
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.io, "inputboolean") as ask, \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs"), \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    ask.assert_not_called()


@pytest.mark.unit
def test_configurerole_fails_when_provisioning_fails():
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value=None), \
         patch.object(console_member.pgrole, "sync_groups") as sg, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is False
    sg.assert_not_called()


# --- OS-user login role (ident maps the OS user to the login role) ----------

@pytest.mark.unit
def test_configurerole_asks_for_the_osuser_and_creates_the_login_role():
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "ensure_os_login_role", return_value=True) as eo, \
         patch.object(console_member.io, "inputstring", return_value="lo_test") as ins, \
         patch.object(console_member.io, "inputboolean", return_value=True), \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs"), \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is True
    ins.assert_called_once()
    eo.assert_called_once()
    assert eo.call_args.args[1:3] == ("lo_test", "m_lo_test")


@pytest.mark.unit
def test_configurerole_blank_osuser_skips_the_login_role():
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "ensure_os_login_role") as eo, \
         patch.object(console_member.io, "inputstring", return_value=""), \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs"), \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is True
    eo.assert_not_called()


@pytest.mark.unit
def test_configurerole_declining_the_login_role_creates_nothing():
    conn = MagicMock()

    def exists(args, name, **kwargs):
        return name == "m_lo_test"  # the member role exists; the OS login role does not

    with patch.object(console_member.database, "rolexists", side_effect=exists), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "ensure_os_login_role") as eo, \
         patch.object(console_member.io, "inputstring", return_value="lo_test"), \
         patch.object(console_member.io, "inputboolean", return_value=False) as ask, \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs") as mp, \
         patch.object(console_member.database, "manage_secondary_role") as ms, \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is False
    ask.assert_called_once()
    assert "login role" in ask.call_args.args[0]
    eo.assert_not_called()
    mp.assert_not_called()
    ms.assert_not_called()


@pytest.mark.unit
def test_configurerole_refused_osuser_is_an_error_not_silent():
    conn = MagicMock()
    with patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "ensure_os_login_role", return_value=False), \
         patch.object(console_member.io, "inputstring", return_value="Bad Name"), \
         patch.object(console_member.io, "inputboolean", return_value=True), \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs"), \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch("bbsengine6.console.member.io.echo") as echo:
        ok = console_member.configurerole(_args(), "lo_test", sysop=False, conn=conn, moniker="lo_test")
    assert ok is False
    assert any("could not create" in str(c.args[0]) for c in echo.call_args_list)
