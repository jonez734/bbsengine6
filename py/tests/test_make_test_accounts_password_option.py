"""scripts/make_test_accounts.py: --password sets every account touched to one password."""

import importlib.util
import pathlib
from unittest.mock import patch

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "make_test_accounts.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("make_test_accounts_pw", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_password_option_sets_every_new_account_to_that_password(tool, tmp_path):
    seen = []
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=False), \
         patch.object(tool, "make_member", side_effect=lambda a, m, pw, **k: seen.append((m, pw))), \
         patch.object(tool, "generate_password") as gen, \
         patch.object(tool, "verify", return_value=True):
        rc = tool.main(["--database", "zoid6test", "-n", "3", "--password", "shared-pw-1",
                        "--credentials", str(tmp_path / "c.md")])
    assert rc == 0
    assert [pw for _, pw in seen] == ["shared-pw-1"] * 3
    gen.assert_not_called()


@pytest.mark.unit
def test_password_option_is_written_to_credentials_for_each_account(tool, tmp_path):
    creds_path = tmp_path / "c.md"
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=False), \
         patch.object(tool, "make_member"), \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "2", "--password", "shared-pw-2",
                   "--credentials", str(creds_path)])
    text = creds_path.read_text()
    assert "| alice | shared-pw-2 |" in text
    assert "| bob | shared-pw-2 |" in text


@pytest.mark.unit
def test_password_option_is_not_echoed_to_stdout(tool, tmp_path, capsys):
    pw = "never-print-this-pw-42"
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=False), \
         patch.object(tool, "make_member"), \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--password", pw,
                   "--credentials", str(tmp_path / "c.md")])
    out = capsys.readouterr()
    assert pw not in out.out and pw not in out.err


@pytest.mark.unit
def test_existing_account_keeps_password_without_reset_even_with_option(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member") as make, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--password", "shared-pw-3",
                   "--credentials", str(tmp_path / "c.md")])
    make.assert_not_called()


@pytest.mark.unit
def test_reset_with_option_sets_existing_account_to_shared_password(tool, tmp_path):
    seen = []
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=True), \
         patch.object(tool, "make_member", side_effect=lambda a, m, pw, **k: seen.append(pw)), \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--reset-passwords",
                   "--password", "shared-pw-4", "--credentials", str(tmp_path / "c.md")])
    assert seen == ["shared-pw-4"]


@pytest.mark.unit
def test_empty_password_is_rejected(tool):
    with patch.object(tool, "database") as db:
        assert tool.main(["--database", "zoid6test", "-n", "1", "--password", ""]) == 2
        db.getpool.assert_not_called()


@pytest.mark.unit
def test_no_password_option_still_generates_random_passwords(tool, tmp_path):
    with patch.object(tool, "database"), \
         patch.object(tool, "member_exists", return_value=False), \
         patch.object(tool, "make_member"), \
         patch.object(tool, "generate_password", return_value="random-pw-xyz-123456") as gen, \
         patch.object(tool, "verify", return_value=True):
        tool.main(["--database", "zoid6test", "-n", "1", "--credentials", str(tmp_path / "c.md")])
    gen.assert_called()
