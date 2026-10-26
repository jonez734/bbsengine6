"""Approval provisions the psql login role for the member's loginid.

The loginid is the OS login. Approval does not ask for an OS username: it ensures the data role
and the login role named for the loginid, and grants the login role the data role. Disapproval
provisions nothing.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.console import memberapproval

M = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y"}


def _process(bools):
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
         patch.object(memberapproval.io, "inputstring", side_effect=AssertionError("no OS prompt")), \
         patch.object(memberapproval.util, "hr"), \
         patch.object(memberapproval.console_member, "_apply_login_role", return_value=True) as apply:
        memberapproval._process_member(object(), {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y"}, "sysop", conn=conn)
    return {"appr": appr, "dis": dis, "elr": elr, "apply": apply, "conn": conn}


@pytest.mark.unit
def test_approval_applies_the_loginid_login_role_without_prompting():
    out = _process([True, True])  # email verified, then approve
    assert out["appr"].called
    out["apply"].assert_called_once()
    assert out["apply"].call_args.args[2] == "lo_test"  # the loginid is the OS login


@pytest.mark.unit
def test_disapproval_provisions_nothing():
    out = _process([True, False])  # email verified, then decline
    out["dis"].assert_called_once()
    out["apply"].assert_not_called()
    out["elr"].assert_not_called()


@pytest.mark.unit
def test_approval_does_not_ask_for_an_os_username():
    # _process patches inputstring to raise if it is called; approval must not reach it.
    out = _process([True, True])
    assert out["appr"].called
