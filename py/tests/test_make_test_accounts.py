"""scripts/make_test_accounts.py: naming, count validation, and the database guard."""

import importlib.util
import pathlib
from unittest.mock import patch

import pytest

SCRIPT = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "make_test_accounts.py"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("make_test_accounts", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_named_accounts_come_first(tool):
    assert tool.names(3) == ["alice", "bob", "charles"]


@pytest.mark.unit
def test_generated_names_follow_the_named_list(tool):
    out = tool.names(10)
    assert out[8:] == ["tester1", "tester2"]
    assert len(set(out)) == 10


@pytest.mark.unit
def test_zero_or_negative_count_rejected(tool):
    with pytest.raises(ValueError):
        tool.names(0)


@pytest.mark.unit
def test_refuses_live_database_by_default(tool):
    with patch.object(tool, "database") as db:
        assert tool.main(["--database", "zoid6", "-n", "1"]) == 2
        db.getpool.assert_not_called()


@pytest.mark.unit
def test_allows_test_databases(tool):
    with patch.object(tool, "database") as db, \
         patch.object(tool, "make_member"), patch.object(tool, "make_bank_account"), \
         patch.object(tool, "verify", return_value=True):
        assert tool.main(["--database", "zoid6test", "-n", "2"]) == 0
        db.getpool.assert_called_once()


@pytest.mark.unit
def test_override_allows_other_database_names(tool):
    with patch.object(tool, "database"), \
         patch.object(tool, "make_member"), patch.object(tool, "make_bank_account"), \
         patch.object(tool, "verify", return_value=True):
        assert tool.main(["--database", "scratch", "--allow-database", "-n", "1"]) == 0
