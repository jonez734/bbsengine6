"""scripts/make_test_accounts.py: random passwords, credentials file, bank skip, reruns."""

import importlib.util
import os
import pathlib
import stat
from unittest.mock import patch

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "make_test_accounts.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("make_test_accounts_creds", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_generated_passwords_are_random_unique_and_long(tool):
    pws = [tool.generate_password() for _ in range(20)]
    assert len(set(pws)) == 20
    assert all(len(p) >= 16 for p in pws)


@pytest.mark.unit
def test_default_password_is_not_the_fixed_test_value(tool):
    assert not hasattr(tool, "DEFAULT_PASSWORD") or tool.DEFAULT_PASSWORD != "test"


@pytest.mark.unit
def test_credentials_file_written_mode_0600(tool, tmp_path):
    path = tmp_path / "zoid6" / "test-accounts.md"
    tool.write_credentials(path, {"alice": "pw-alice-123456789", "bob": "pw-bob-1234567890"})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700
    text = path.read_text()
    assert "alice" in text and "pw-alice-123456789" in text
    assert "bob" in text and "pw-bob-1234567890" in text


@pytest.mark.unit
def test_passwords_not_echoed_to_stdout(tool, tmp_path, capsys):
    pw = "unique-secret-pw-9876543210"
    with patch.object(tool, "database"), \
         patch.object(tool, "make_member"), \
         patch.object(tool, "verify", return_value=True), \
         patch.object(tool, "generate_password", return_value=pw):
        tool.main(["--database", "zoid6test", "-n", "1", "--credentials", str(tmp_path / "c.md")])
    out = capsys.readouterr()
    assert pw not in out.out and pw not in out.err


@pytest.mark.unit
def test_skip_bank_is_default_and_creates_no_bank_rows(tool):
    with patch.object(tool, "database"), \
         patch.object(tool, "make_member"), \
         patch.object(tool, "make_bank_account") as bank, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "2"])
    bank.assert_not_called()


@pytest.mark.unit
def test_live_database_refused_without_allow_flag(tool):
    with patch.object(tool, "database") as db:
        assert tool.main(["--database", "zoid6", "-n", "1"]) == 2
        db.getpool.assert_not_called()


@pytest.mark.unit
def test_existing_account_keeps_its_password_on_rerun(tool):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member") as make, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1"])
    make.assert_not_called()


@pytest.mark.unit
def test_reset_passwords_flag_sets_a_new_password(tool):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member") as make, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--reset-passwords"])
    make.assert_called_once()
