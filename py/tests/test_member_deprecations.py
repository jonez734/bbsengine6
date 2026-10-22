"""getcurrentid and getbyid are removed (they raise); getcurrent works by moniker."""

from unittest.mock import MagicMock, patch

import pytest

from bbsengine6.member import lib as member_lib

ARGS = MagicMock(debug=False)


@pytest.mark.unit
def test_getcurrentid_raises_and_names_replacement():
    with pytest.raises(RuntimeError, match="getcurrentmoniker"):
        member_lib.getcurrentid(ARGS)


@pytest.mark.unit
def test_getbyid_raises_and_names_replacement():
    with pytest.raises(RuntimeError, match="getbymoniker"):
        member_lib.getbyid(ARGS, 1)


@pytest.mark.unit
def test_getcurrent_uses_moniker_not_id():
    with patch.object(member_lib, "getcurrentmoniker", return_value="jam"), \
         patch.object(member_lib, "getbymoniker", return_value={"moniker": "jam", "credits": 3}) as gbm:
        rec = member_lib.getcurrent(ARGS, "moniker, credits")
    assert rec["moniker"] == "jam"
    assert gbm.call_args.args[1] == "jam"


@pytest.mark.unit
def test_getcurrent_returns_none_without_a_moniker():
    with patch.object(member_lib, "getcurrentmoniker", return_value=None):
        assert member_lib.getcurrent(ARGS) is None
