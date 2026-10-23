"""member.getbalance: bed bank first, then the local bank account, then member.credits.

A real zero balance is shown as 0. A missing bank account falls back to credits. Bed is supplied
by the caller as bed_fetch; these tests pass a fake.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib
from _bed_fetch_fake import fake

ARGS = MagicMock(debug=False)


def _bed_ok(balance, account=True):
    return {"balance": balance, "account": account}


@pytest.mark.unit
def test_bed_account_returns_bed_balance():
    with patch.object(member_lib, "_db_account") as db, \
         patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(_bed_ok(250))) == 250
    db.assert_not_called()
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_down_uses_local_account_balance():
    with patch.object(member_lib, "_db_account", return_value={"balance": 75}), \
         patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(side_effect=ConnectionError("down"))) == 75
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_down_no_local_account_falls_back_to_credits():
    with patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 40}):
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(side_effect=ConnectionError("down"))) == 40


@pytest.mark.unit
def test_real_zero_balance_is_zero_not_credits():
    with patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(_bed_ok(0, account=True))) == 0
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_reports_no_account_falls_back_to_credits():
    with patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 12}):
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(_bed_ok(0, account=False))) == 12


@pytest.mark.unit
def test_moniker_defaults_to_current_moniker():
    bf = fake(_bed_ok(9))
    with patch.object(member_lib, "getcurrentmoniker", return_value="jam") as cm:
        assert member_lib.getbalance(ARGS, bed_fetch=bf) == 9
    cm.assert_called_once()
    assert bf.call_args.args[1] == "jam"


@pytest.mark.unit
def test_bed_no_account_but_local_row_uses_local_balance():
    with patch.object(member_lib, "_db_account", return_value={"balance": 500}), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 12}):
        assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake(_bed_ok(0, account=False))) == 500
