"""A new member's data role is created without CREATEDB/CREATEROLE, so configurerole must not
ALTER it to revoke them. manage_role_privs runs as zoid6 (no CREATEROLE), so that ALTER fails
with InsufficientPrivilege and aborts the add. Sysop grants (createdb/createrole for a sysop)
still apply, since those are real changes.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import member as console_member


def _run(sysop, role_created):
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.database, "get_role_privs", return_value={"rolsuper": False}), \
         patch.object(console_member.database, "manage_role_privs") as mp, \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch.object(console_member.database, "rolexists", return_value=not role_created), \
         patch.object(console_member.io, "echo"):
        console_member.configurerole(object(), "lo_test", sysop=sysop, conn=conn,
                                     moniker="lo_test", osuser=None, psqlrole=None, menu_answered=True)
    return [(c.args[2], c.args[3]) for c in mp.call_args_list]


@pytest.mark.unit
def test_non_sysop_new_role_issues_no_createdb_or_createrole_alter():
    calls = _run(sysop=False, role_created=True)
    assert ("revoke", "createdb") not in calls and ("revoke", "createrole") not in calls, calls


@pytest.mark.unit
def test_sysop_still_gets_createdb_and_createrole():
    calls = _run(sysop=True, role_created=True)
    assert ("grant", "createdb") in calls and ("grant", "createrole") in calls, calls


def _run_with_privs(privs):
    conn = MagicMock()
    with patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.database, "get_role_privs", return_value=privs), \
         patch.object(console_member.database, "manage_role_privs") as mp, \
         patch.object(console_member.database, "manage_secondary_role"), \
         patch.object(console_member.database, "rolexists", return_value=True), \
         patch.object(console_member.io, "echo"):
        console_member.configurerole(object(), "lo_test", sysop=False, conn=conn,
                                     moniker="lo_test", osuser=None, psqlrole=None, menu_answered=True)
    return [(c.args[2], c.args[3]) for c in mp.call_args_list]


@pytest.mark.unit
def test_revoke_skipped_when_role_already_lacks_createdb_and_createrole():
    """The role exists (so 'preexisting' is true) but holds no CREATEDB/CREATEROLE. An ALTER here
    would fail with InsufficientPrivilege, so it must not be issued."""
    calls = _run_with_privs({"rolsuper": False, "rolcreatedb": False, "rolcreaterole": False})
    assert ("revoke", "createdb") not in calls and ("revoke", "createrole") not in calls, calls


@pytest.mark.unit
def test_revoke_issued_only_for_the_privilege_the_role_actually_holds():
    calls = _run_with_privs({"rolsuper": False, "rolcreatedb": True, "rolcreaterole": False})
    assert ("revoke", "createdb") in calls, calls
    assert ("revoke", "createrole") not in calls, calls
