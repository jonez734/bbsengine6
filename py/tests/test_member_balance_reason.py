"""getbalance_info explains why bed's balance was not used, on a separate debug echo.

Reasons: ok, no_token, bed_refused: <code>, bed_down: <exception>, no_bank_account.
The source label and the number are unchanged.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib

ARGS = MagicMock(debug=False)


def _reason(bed_result=None, bed_exc=None, local=None):
    kw = {}
    with patch.object(member_lib, "_bed_balance", side_effect=bed_exc, return_value=bed_result) as bb, \
         patch.object(member_lib, "_db_account", return_value=local), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 1}), \
         patch.object(member_lib.io, "echo") as echo:
        info = member_lib.getbalance_info(ARGS, "alice")
    text = " ".join(str(c.args[0]) for c in echo.call_args_list if c.args)
    return info, text


@pytest.mark.unit
def test_reason_ok_when_bed_answers_with_an_account():
    info, text = _reason(bed_result={"balance": 5, "account": True, "bed_name": "zoid6"})
    assert info["reason"] == "ok"
    assert "reason: ok" in text


@pytest.mark.unit
def test_reason_bed_refused_names_the_error_code():
    from bed.client.exceptions import BedUnavailable
    info, text = _reason(bed_exc=BedUnavailable("bank_balance: not_authenticated: Authentication required"))
    assert info["reason"].startswith("bed_down") or info["reason"].startswith("bed_refused")
    assert "reason:" in text


@pytest.mark.unit
def test_reason_no_bank_account():
    info, _ = _reason(bed_result={"balance": 0, "account": False}, local=None)
    assert info["reason"] == "no_bank_account"


@pytest.mark.unit
def test_reason_bed_down_names_the_exception():
    info, _ = _reason(bed_exc=ConnectionError("refused"), local={"balance": 7})
    assert info["reason"] == "bed_down: ConnectionError"
    assert info["source"] == "bank"


@pytest.mark.unit
def test_reason_is_on_a_separate_debug_echo_not_the_result_number():
    info, text = _reason(bed_result={"balance": 5, "account": True, "bed_name": "zoid6"})
    assert info["balance"] == 5
    assert "reason:" in text


@pytest.mark.unit
def test_reason_no_token_when_no_token_is_available():
    with patch.object(member_lib, "_resolve_bed_token", return_value=""), \
         patch.object(member_lib, "_bed_balance") as bb, \
         patch.object(member_lib, "_db_account", return_value={"balance": 9}), \
         patch.object(member_lib.io, "echo") as echo:
        info = member_lib.getbalance_info(ARGS, "alice")
    bb.assert_not_called()
    assert info["reason"] == "no_token"
    assert info["source"] == "bank"
    assert any("reason: no_token" in str(c.args[0]) for c in echo.call_args_list if c.args)


@pytest.mark.unit
def test_reason_echo_names_the_bed_when_bed_answers():
    info, text = _reason(bed_result={"balance": 5, "account": True, "bed_name": "zoid6"})
    assert "reason: ok bed=zoid6" in text


@pytest.mark.unit
def test_reason_echo_without_a_bed_name_has_no_bed_field():
    _, text = _reason(bed_result={"balance": 5, "account": True})
    assert "reason: ok" in text
    assert "bed=" not in text


@pytest.mark.unit
def test_reason_echo_when_bed_is_down_names_no_bed():
    _, text = _reason(bed_exc=ConnectionError("refused"), local={"balance": 7})
    assert "reason: bed_down: ConnectionError" in text
    assert "bed=" not in text
