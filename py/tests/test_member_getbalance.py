"""member.getbalance: bed bank first, then the local bank account, then member.credits.

A real zero balance is shown as 0. A missing bank account falls back to credits.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib


ARGS = MagicMock(debug=False)


def _bed_ok(balance, account=True):
    return {"balance": balance, "account": account}


@pytest.mark.unit
def test_bed_account_returns_bed_balance():
    with patch.object(member_lib, "_bed_balance", return_value=_bed_ok(250)), \
         patch.object(member_lib, "_db_account") as db, \
         patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice") == 250
    db.assert_not_called()
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_down_uses_local_account_balance():
    with patch.object(member_lib, "_bed_balance", side_effect=ConnectionError("down")), \
         patch.object(member_lib, "_db_account", return_value={"balance": 75}), \
         patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice") == 75
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_down_no_local_account_falls_back_to_credits():
    with patch.object(member_lib, "_bed_balance", side_effect=ConnectionError("down")), \
         patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 40}):
        assert member_lib.getbalance(ARGS, "alice") == 40


@pytest.mark.unit
def test_real_zero_balance_is_zero_not_credits():
    with patch.object(member_lib, "_bed_balance", return_value=_bed_ok(0, account=True)), \
         patch.object(member_lib, "getcurrent") as gc:
        assert member_lib.getbalance(ARGS, "alice") == 0
    gc.assert_not_called()


@pytest.mark.unit
def test_bed_reports_no_account_falls_back_to_credits():
    with patch.object(member_lib, "_bed_balance", return_value=_bed_ok(0, account=False)), \
         patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 12}):
        assert member_lib.getbalance(ARGS, "alice") == 12


@pytest.mark.unit
def test_moniker_defaults_to_current_moniker():
    with patch.object(member_lib, "getcurrentmoniker", return_value="jam") as cm, \
         patch.object(member_lib, "_bed_balance", return_value=_bed_ok(9)) as bb:
        assert member_lib.getbalance(ARGS) == 9
    cm.assert_called_once()
    assert bb.call_args.args[1] == "jam"


@pytest.mark.unit
def test_bed_no_account_but_local_row_uses_local_balance():
    with patch.object(member_lib, "_bed_balance", return_value=_bed_ok(0, account=False)), \
         patch.object(member_lib, "_db_account", return_value={"balance": 500}), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 12}):
        assert member_lib.getbalance(ARGS, "alice") == 500


@pytest.mark.unit
def test_bed_balance_closes_its_socket_on_the_request_loop():
    import asyncio
    seen = {}

    class FakeWs:
        async def close(self):
            seen["close_loop"] = asyncio.get_running_loop()

    class FakeConn:
        _ws = FakeWs()

    async def fake_request(self, msg):
        seen["request_loop"] = asyncio.get_running_loop()
        return {"balance": 1, "account": True}

    with patch("bed.client.get_bed_connection", return_value=FakeConn()), \
         patch("bed.client.bank.BedBankClient._request", fake_request):
        member_lib._bed_balance(ARGS, "alice")
    assert seen["close_loop"] is seen["request_loop"]
