"""A new member gets a bank account as a named step in the add flow, before the commit.

The starting balance comes from bank.starting_balance in bed.json (default 100). It is applied
through bbsengine6.bank.configure, the same way session.idle_minutes reaches the session module.
A failure in this step rolls back the whole add and names the step.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6 import bank
from bbsengine6.bank import bank as bankmod
from bbsengine6.console import member as console_member


def test_default_starting_balance_is_100():
    assert bankmod.DEFAULT_STARTING_BALANCE == 100


def test_configure_sets_the_starting_balance():
    try:
        bank.configure(starting_balance=250)
        assert bank.get_starting_balance() == 250
    finally:
        bank.configure(starting_balance=bankmod.DEFAULT_STARTING_BALANCE)


def test_configure_rejects_a_negative_balance():
    with pytest.raises(ValueError):
        bank.configure(starting_balance=-1)


def test_configure_rejects_a_non_integer_balance():
    with pytest.raises(ValueError):
        bank.configure(starting_balance="100")
    with pytest.raises(ValueError):
        bank.configure(starting_balance=True)


def test_add_creates_the_bank_account_with_the_starting_balance():
    args = MagicMock(debug=False)
    conn = MagicMock()
    member = {"moniker": "lo_test", "loginid": "lo_test", "password": None, "flags": {}}
    with patch.object(console_member.libmember, "insert", return_value="lo_test"), \
         patch.object(console_member.bank, "BankService") as svc, \
         patch.object(console_member, "configurerole", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "sync_groups", return_value=True), \
         patch.object(console_member.io, "echo"):
        ok = console_member._add_write(args, member, conn=conn)
    assert ok is True
    svc.return_value.add_funds.assert_called()
    assert svc.return_value.add_funds.call_args.args[1] == bank.get_starting_balance()


def test_bank_account_step_runs_before_commit_and_after_insert():
    order = []
    args = MagicMock(debug=False)
    conn = MagicMock()
    conn.commit.side_effect = lambda: order.append("commit")
    member = {"moniker": "lo_test", "loginid": "lo_test", "password": None, "flags": {}}
    with patch.object(console_member.libmember, "insert",
                      side_effect=lambda *a, **k: order.append("insert") or "lo_test"), \
         patch.object(console_member.bank, "BankService") as svc, \
         patch.object(console_member, "configurerole", return_value=True), \
         patch.object(console_member.pgrole, "ensure_login_role", return_value="m_lo_test"), \
         patch.object(console_member.pgrole, "sync_groups", return_value=True), \
         patch.object(console_member.io, "echo"):
        svc.return_value.add_funds.side_effect = lambda *a, **k: order.append("bank")
        console_member._add_write(args, member, conn=conn)
    assert order.index("insert") < order.index("bank") < order.index("commit"), order


def test_bank_failure_rolls_back_and_names_the_step():
    args = MagicMock(debug=False)
    conn = MagicMock()
    member = {"moniker": "lo_test", "loginid": "lo_test", "password": None, "flags": {}}
    with patch.object(console_member.libmember, "insert", return_value="lo_test"), \
         patch.object(console_member.bank, "BankService") as svc, \
         patch.object(console_member.io, "echo") as echo, \
         patch.object(console_member.io, "echo_traceback"):
        svc.return_value.add_funds.side_effect = RuntimeError("bank down")
        ok = console_member._add_write(args, member, conn=conn)
    assert ok is False
    conn.rollback.assert_called()
    msgs = " ".join(str(c.args[0]) for c in echo.call_args_list)
    assert "bank account" in msgs and "No changes were saved" in msgs
