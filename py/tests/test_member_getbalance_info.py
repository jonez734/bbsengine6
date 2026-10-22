"""member.getbalance_info reports the balance and its source; getbalance returns only the number.

Sources: "bed" (bed's bank), "bank" (the local bank account), "credits" (member.credits).
A NULL credits value counts as 0.
"""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib

ARGS = MagicMock(debug=False)


@pytest.mark.unit
def test_info_reports_bed_source():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 250, "account": True}):
        assert member_lib.getbalance_info(ARGS, "alice") == {"balance": 250, "source": "bed bank"}


@pytest.mark.unit
def test_info_reports_bank_source_when_bed_down():
    with patch.object(member_lib, "_bed_balance", side_effect=ConnectionError("down")), \
         patch.object(member_lib, "_db_account", return_value={"balance": 75}):
        assert member_lib.getbalance_info(ARGS, "alice") == {"balance": 75, "source": "bank"}


@pytest.mark.unit
def test_info_reports_credits_source_when_no_bank_account():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 0, "account": False}), \
         patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": 40}):
        assert member_lib.getbalance_info(ARGS, "alice") == {"balance": 40, "source": "credits"}


@pytest.mark.unit
def test_null_credits_counts_as_zero():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 0, "account": False}), \
         patch.object(member_lib, "_db_account", return_value=None), \
         patch.object(member_lib, "getcurrent", return_value={"credits": None}):
        assert member_lib.getbalance_info(ARGS, "alice") == {"balance": 0, "source": "credits"}


@pytest.mark.unit
def test_getbalance_returns_only_the_number_of_info():
    with patch.object(member_lib, "_bed_balance", return_value={"balance": 250, "account": True}):
        assert member_lib.getbalance(ARGS, "alice") == 250


@pytest.mark.unit
def test_info_returns_none_without_a_member():
    with patch.object(member_lib, "getcurrentmoniker", return_value=None):
        assert member_lib.getbalance_info(ARGS) is None
