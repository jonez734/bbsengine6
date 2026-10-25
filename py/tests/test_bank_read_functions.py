"""Bank balance and transaction reads go through SECURITY DEFINER functions, not the views.

A plain grant on bank.account or bank.transaction gives every member every row. The functions
check the caller first and return only that member's rows. The views are no longer granted to
member, so a member cannot read every balance or every transaction.
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkfunctions

SQL = Path(pgrole.__file__).parent / "sql" / "bank_read_functions.sql"


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


@pytest.mark.unit
def test_read_functions_file_exists():
    assert SQL.is_file(), SQL


@pytest.mark.unit
def test_both_functions_are_defined():
    t = _code(SQL.read_text())
    assert re.search(r"FUNCTION\s+bank\.get_balance\s*\(\s*p_moniker\s+citext\s*\)", t, re.I)
    assert re.search(r"FUNCTION\s+bank\.get_transactions\s*\(\s*p_moniker\s+citext\s*,\s*p_limit\s+int(\s+default\s+\d+)?\s*\)", t, re.I)


@pytest.mark.unit
def test_functions_are_security_definer_with_pinned_search_path():
    t = _code(SQL.read_text())
    assert t.lower().count("security definer") >= 2
    assert t.lower().count("set search_path") >= 2


@pytest.mark.unit
def test_functions_are_owned_by_zoid6():
    t = _code(SQL.read_text())
    assert len(re.findall(r"OWNER\s+TO\s+zoid6", t, re.I)) >= 2


@pytest.mark.unit
def test_access_check_is_membership_in_the_data_role_or_sysop_term():
    t = _code(SQL.read_text()).lower()
    assert "pg_has_role(session_user" in t or "pg_has_role(current_user" in t
    assert "'m_' || p_moniker" in t or "'m_'||p_moniker" in t
    assert "'sysop'" in t and "'term'" in t


@pytest.mark.unit
def test_access_is_checked_before_any_row_is_returned():
    """The membership test must come before the SELECT that returns rows."""
    t = _code(SQL.read_text()).lower()
    for fn in ("get_balance", "get_transactions"):
        body = t[t.index(f"function bank.{fn}"):]
        check = body.find("pg_has_role")
        select = body.find("select", body.find("begin") if "begin" in body else 0)
        assert check != -1, fn
        assert check < body.find("return query") + 1 or check < body.find("select"), fn


@pytest.mark.unit
def test_member_gets_execute_and_loses_view_access():
    t = _code(SQL.read_text()).lower()
    assert re.search(r"grant\s+execute\s+on\s+function\s+bank\.get_balance\(citext\)\s+to\s+member", t)
    assert re.search(r"grant\s+execute\s+on\s+function\s+bank\.get_transactions\(citext,\s*int\)\s+to\s+member", t)
    assert re.search(r"revoke\s+select\s+on\s+bank\.account\s+from\s+member", t)
    assert re.search(r"revoke\s+select\s+on\s+bank\.transaction\s+from\s+member", t)


@pytest.mark.unit
def test_functions_are_installed_by_checkfunctions():
    src = Path(checkfunctions.__file__).read_text()
    assert '"bank.get_balance"' in src
    assert '"bank.get_transactions"' in src
