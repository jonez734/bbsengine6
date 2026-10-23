"""getbalance_info labels a bed-bank balance with the bed's name: "<name> bank".

Without a name from bed, the label is "bed bank". Local bank and credits labels are unchanged.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib
from _bed_fetch_fake import fake

ARGS = MagicMock(debug=False)


@pytest.mark.unit
def test_bed_balance_labelled_with_bed_name():
    info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=fake({"balance": 250, "account": True, "bed_name": "zoid6"}))
    assert info["source"] == "zoid6 bank"
    assert info["balance"] == 250


@pytest.mark.unit
def test_bed_balance_without_a_name_is_labelled_bed_bank():
    info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=fake({"balance": 250, "account": True}))
    assert info["source"] == "bed bank"


@pytest.mark.unit
def test_local_bank_label_unchanged():
    with patch.object(member_lib, "_db_account", return_value={"balance": 75}):
        info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=fake(side_effect=ConnectionError("down")))
    assert info["source"] == "bank"


@pytest.mark.unit
def test_credits_label_unchanged():
    with patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 40}):
        info = member_lib.getbalance_info(ARGS, "alice", bed_fetch=fake({"balance": 0, "account": False}))
    assert info["source"] == "credits"


@pytest.mark.unit
def test_getbalance_still_returns_only_the_number():
    assert member_lib.getbalance(ARGS, "alice", bed_fetch=fake({"balance": 250, "account": True, "bed_name": "zoid6"})) == 250
