"""Graceful errors around member insert and update.

A database failure must not print a raw traceback to the sysop as the only signal. Each write
is rolled back, the sysop gets one readable line naming the step, and the menu stays usable.
The stack trace is kept in the log.
"""

from unittest.mock import MagicMock, patch

import psycopg
import pytest

from bbsengine6.console import member as console_member
from bbsengine6.member import lib as libmember


def _args():
    return type("A", (), {"debug": False})()


@pytest.mark.unit
def test_insert_reports_a_database_error_as_a_failure_not_a_raise():
    member = {"moniker": "lo_test", "loginid": "lo_test", "email": "x@y", "flags": {}}
    with patch.object(libmember.database, "insert", side_effect=psycopg.errors.CheckViolation("bad")), \
         patch.object(libmember, "_validate_moniker_shape"), \
         patch.object(libmember.io, "echo"):
        result = libmember.insert(_args(), member, conn=MagicMock())
    assert result is False


@pytest.mark.unit
def test_update_reports_a_database_error_as_false_and_rolls_back():
    member = {"moniker": "lo_test", "email": "x@y", "flags": {"SYSOP": {"value": True}}}
    conn = MagicMock()
    with patch.object(libmember, "getcurrentmoniker", return_value="jam"), \
         patch.object(libmember, "_update_member_flags", side_effect=psycopg.errors.UndefinedTable("gone")), \
         patch.object(libmember.io, "echo"), \
         patch.object(libmember.util, "logentry") as log:
        result = libmember.update(_args(), member, "lo_test", conn=conn)
    assert result is False
    conn.rollback.assert_called()


@pytest.mark.unit
def test_add_rolls_back_and_says_which_step_failed():
    conn = MagicMock()
    member = {"moniker": "lo_test", "loginid": "lo_test", "password": "x", "flags": {}}
    with patch.object(console_member.libmember, "insert", side_effect=psycopg.errors.CheckViolation("bad")), \
         patch.object(console_member.io, "echo") as echo, \
         patch.object(console_member.io, "echo_traceback") as tb:
        ok = console_member._add_write(_args(), member, conn=conn)
    assert ok is False
    conn.rollback.assert_called_once()
    msgs = [str(c.args[0]) for c in echo.call_args_list]
    assert any("insert" in m.lower() and "lo_test" in m for m in msgs), msgs
    tb.assert_called_once()


@pytest.mark.unit
def test_edit_reports_a_failed_update_and_does_not_continue():
    conn = MagicMock()
    m = {"moniker": "lo_test", "loginid": "lo_test", "password": "x", "flags": {}, "email": "x@y"}
    with patch.object(console_member.libmember, "update", return_value=False), \
         patch.object(console_member.libmember, "setpassword") as sp, \
         patch.object(console_member.io, "echo") as echo, \
         patch.object(console_member.io, "echo_traceback"):
        ok = console_member._edit_write(_args(), m, _baseline_flags={}, _baseline_email="x@y", conn=conn)
    assert ok is False
    sp.assert_not_called()
    conn.rollback.assert_called_once()
    assert any("update" in str(c.args[0]).lower() for c in echo.call_args_list)


@pytest.mark.unit
def test_successful_add_commits_once():
    conn = MagicMock()
    member = {"moniker": "lo_test", "loginid": "lo_test", "password": None, "flags": {}}
    with patch.object(console_member.libmember, "insert", return_value="lo_test"), \
         patch.object(console_member.bank, "BankService"), \
         patch.object(console_member, "configurerole", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "sync_groups", return_value=True), \
         patch.object(console_member.io, "echo"):
        ok = console_member._add_write(_args(), member, conn=conn)
    assert ok is True
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
