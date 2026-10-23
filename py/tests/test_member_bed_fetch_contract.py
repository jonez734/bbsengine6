"""getbalance_info takes the bed step as a callable (bed_fetch), not an import.

With no bed_fetch, bed is not consulted and the reason is no_bed_source. The order of sources and
their labels are unchanged: bed, then the local bank, then credits.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib

ARGS = MagicMock(debug=False)


def _ok(balance, account=True, bed_name="zoid6"):
    return {"balance": balance, "account": account, "bed_name": bed_name}


@pytest.fixture(autouse=True)
def _db_and_credits():
    with patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 75}):
        yield


def test_bed_fetch_supplies_the_bed_source():
    info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=lambda a, m: _ok(250))
    assert info == {"balance": 250, "source": "zoid6 bank", "reason": "ok"}


def test_without_bed_fetch_bed_is_not_consulted():
    info = member_lib.getbalance_info(ARGS, "alice")
    assert info["reason"] == "no_bed_source"
    assert info["source"] == "credits"
    assert info["balance"] == 75


def test_without_bed_fetch_local_bank_still_wins_over_credits():
    with patch.object(member_lib, "_db_account", return_value={"balance": 40}):
        info = member_lib.getbalance_info(ARGS, "alice")
    assert info == {"balance": 40, "source": "bank", "reason": "no_bed_source"}


def test_bed_fetch_is_called_with_the_args_and_moniker():
    seen = {}

    def fetch(a, m):
        seen["args"], seen["moniker"] = a, m
        return _ok(1)

    member_lib.getbalance_info(ARGS, "alice", bed_fetch=fetch)
    assert seen == {"args": ARGS, "moniker": "alice"}


def test_bed_refusal_falls_back_to_local_bank():
    def refuse(a, m):
        exc = RuntimeError("no")
        exc.code = "token_invalid"
        raise exc

    with patch.object(member_lib, "_db_account", return_value={"balance": 40}):
        info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=refuse)
    assert info == {"balance": 40, "source": "bank", "reason": "bed_refused: token_invalid"}


def test_bed_down_falls_back_to_credits():
    def down(a, m):
        raise ConnectionError("down")

    info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=down)
    assert info == {"balance": 75, "source": "credits", "reason": "bed_down: ConnectionError"}


def test_bed_without_an_account_falls_through():
    info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=lambda a, m: _ok(0, account=False))
    assert info["reason"] == "no_bank_account"
    assert info["source"] == "credits"


def test_no_bed_source_is_echoed_at_debug_level():
    with patch.object(member_lib, "_balance_reason_echo") as echo:
        member_lib.getbalance_info(ARGS, "alice")
    assert any(c.args[0] == "no_bed_source" for c in echo.call_args_list)
