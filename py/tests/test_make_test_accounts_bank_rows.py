"""scripts/make_test_accounts.py: --with-bank opens a bank row for existing members too.

Existing passwords are kept unless --reset-passwords is given. The starting balance
comes from --bank-balance (default 0). An existing bank row keeps its balance.
"""

import importlib.util
import pathlib
from unittest.mock import patch

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "make_test_accounts.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("make_test_accounts_bank_rows", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_bank_step_runs_for_an_existing_member(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member") as make, \
         patch.object(tool, "make_bank_account") as bank, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--with-bank", "--credentials", str(tmp_path / "c.md")])
    make.assert_not_called()
    bank.assert_called_once()


@pytest.mark.unit
def test_existing_member_password_is_not_changed_by_bank_step(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member") as make, \
         patch.object(tool, "make_bank_account"), \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--with-bank", "--credentials", str(tmp_path / "c.md")])
    make.assert_not_called()


@pytest.mark.unit
def test_bank_balance_option_passes_the_starting_balance(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_bank_account") as bank, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--with-bank", "--bank-balance", "100",
                   "--credentials", str(tmp_path / "c.md")])
    assert bank.call_args.kwargs["balance"] == 100


@pytest.mark.unit
def test_bank_balance_defaults_to_zero(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_bank_account") as bank, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--with-bank", "--credentials", str(tmp_path / "c.md")])
    assert bank.call_args.kwargs["balance"] == 0


@pytest.mark.unit
def test_make_bank_account_default_is_zero_not_100000(tool):
    import inspect
    default = inspect.signature(tool.make_bank_account).parameters["balance"].default
    assert default == 0


@pytest.mark.unit
def test_make_bank_account_keeps_an_existing_balance(tool):
    import inspect
    src = inspect.getsource(tool.make_bank_account)
    assert "ON CONFLICT (moniker) DO NOTHING" in src
