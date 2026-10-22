"""getbalance_info labels a bed-bank balance with the bed's name: "<name> bank".

Without a name from bed, the label is "bed bank". Local bank and credits labels are unchanged.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib

ARGS = MagicMock(debug=False)


@pytest.mark.unit
def test_bed_balance_labelled_with_bed_name():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 250, "account": True, "bed_name": "zoid6"}):
        info = member_lib.getbalance_info(ARGS, "alice")
    assert info["source"] == "zoid6 bank"
    assert info["balance"] == 250


@pytest.mark.unit
def test_bed_balance_without_a_name_is_labelled_bed_bank():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 250, "account": True}):
        assert member_lib.getbalance_info(ARGS, "alice")["source"] == "bed bank"


@pytest.mark.unit
def test_local_bank_label_unchanged():
    with patch.object(member_lib, "_bed_balance", side_effect=ConnectionError("down")), \
         patch.object(member_lib, "_db_account", return_value={"balance": 75}):
        assert member_lib.getbalance_info(ARGS, "alice")["source"] == "bank"


@pytest.mark.unit
def test_credits_label_unchanged():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 0, "account": False}), \
         patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 40}):
        assert member_lib.getbalance_info(ARGS, "alice")["source"] == "credits"


@pytest.mark.unit
def test_getbalance_still_returns_only_the_number():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 250, "account": True, "bed_name": "zoid6"}):
        assert member_lib.getbalance(ARGS, "alice") == 250
