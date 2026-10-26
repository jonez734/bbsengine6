"""[X] data role menu option in the member console. The OS login is the loginid, so there is no
[O] option; the loginid's login role is applied by configurerole.

Each option checks existence right after its input, and writes nothing. The
member dict carries the answers; configurerole applies them when the menu exits.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import member as console_member


def _no_stored_rows(conn):
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
    return conn


def _member(**over):
    m = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y", "ui": None,
         "credits": 0, "refcode": None, "flags": {}, "password": None,
         "psqlrole": None}
    m.update(over)
    return m


def _run_edit(choices, member, **patches):
    """Drive _edit through a scripted sequence of menu choices."""
    seq = iter(choices)
    with patch.object(console_member.io, "inputchoice", side_effect=lambda *a, **k: next(seq)), \
         patch.object(console_member.util, "heading"), \
         patch("bbsengine6.console.member.io.echo"), \
         patch.object(console_member, "render_member"):
        return console_member._edit(object(), "edit", member, conn=_no_stored_rows(MagicMock()), **patches)





@pytest.mark.unit
def test_data_role_option_checks_existence_on_the_chosen_name():
    m = _member()
    seen = {}

    def exists(args, name, **kwargs):
        seen["name"] = name
        return True

    with patch.object(console_member.database, "rolexists", side_effect=exists), \
         patch.object(console_member.io, "inputstring", return_value="m_custom"), \
         patch.object(console_member.database, "createrol") as cr:
        out = _run_edit(["X", "Q"], m)
    assert seen["name"] == "m_custom"
    cr.assert_not_called()
    assert out["psqlrole"] == "m_custom"


@pytest.mark.unit
def test_data_role_option_defaults_to_the_moniker_role():
    m = _member()
    with patch.object(console_member.io, "inputstring", return_value="m_lo_test") as ins, \
         patch.object(console_member.database, "rolexists", return_value=True):
        _run_edit(["X", "Q"], m)
    assert ins.call_args.args[1] == "m_lo_test"


@pytest.mark.unit
def test_existing_data_role_cannot_be_renamed_from_the_menu():
    m = _member(psqlrole="m_lo_test")
    stored = {"exists": True}
    with patch.object(console_member, "_stored_psqlrole", return_value="m_lo_test"), \
         patch.object(console_member.io, "inputstring", return_value="m_other"), \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.io, "inputboolean") as ask:
        out = _run_edit(["X", "Q"], m, mode_existing=True)
    assert out["psqlrole"] == "m_lo_test", "stored data role must not change"


@pytest.mark.unit
def test_configurerole_uses_menu_answers_without_reprompting():
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.io, "inputstring") as ins, \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs"), \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch("bbsengine6.console.member.io.echo"):
        ok = console_member.configurerole(
            object(), "lo_test", sysop=False, conn=conn, moniker="lo_test",
            psqlrole="m_lo_test", menu_answered=True,
        )
    assert ok is True
    ins.assert_not_called()


@pytest.mark.unit
def test_chosen_data_role_name_is_used_for_a_new_member():
    from bbsengine6 import pgrole
    conn = _no_stored_rows(MagicMock())
    with patch.object(pgrole.database, "rolexists", return_value=False), \
         patch.object(pgrole.database, "createrol", return_value=True) as cr, \
         patch.object(pgrole.database, "manage_schema_priv"):
        out = pgrole._ensure_login_role(object(), "lo_test", conn=conn, rolname="m_custom")
    assert cr.call_args.args[1] == "m_custom"
    assert out == "m_custom"


@pytest.mark.unit
def test_stored_data_role_name_wins_over_a_chosen_one():
    from bbsengine6 import pgrole
    conn = MagicMock()
    conn.cursor.return_value.__enter__.return_value.fetchone.return_value = {"rolname": "m_lo_test"}
    with patch.object(pgrole.database, "createrol") as cr, \
         patch.object(pgrole.database, "get_role_privs", return_value={"rolsuper": False, "rolcanlogin": False}), \
         patch.object(pgrole.database, "rolexists", return_value=True):
        out = pgrole._ensure_login_role(object(), "lo_test", conn=conn, rolname="m_other")
    cr.assert_not_called()
    assert out == "m_lo_test"
