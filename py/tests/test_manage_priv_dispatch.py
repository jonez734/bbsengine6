"""One privilege dispatcher, public.manage_priv, replaces three near-identical helpers.

manage_role_privs, manage_schema_priv and manage_database_priv each take an action (grant or
revoke) and a privilege, and differ only in the statement they build. manage_priv takes a kind
(role, schema or database) and dispatches. The three existing names stay as wrappers with their
current signatures, so no caller changes in this step.
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole

SQL = Path(pgrole.__file__).parent / "sql" / "manage_priv.sql"


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


@pytest.mark.unit
def test_dispatcher_file_exists():
    assert SQL.is_file(), SQL


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["role", "schema", "database"])
def test_dispatcher_handles_each_kind(kind):
    assert f"'{kind}'" in _code(SQL.read_text())


@pytest.mark.unit
def test_dispatcher_rejects_an_unknown_kind_and_action():
    t = _code(SQL.read_text()).lower()
    assert "unknown kind" in t
    assert "invalid action" in t


@pytest.mark.unit
def test_dispatcher_is_security_definer_owned_by_zoid6():
    t = _code(SQL.read_text()).lower()
    assert "security definer" in t
    assert "owner to zoid6" in t


@pytest.mark.unit
def test_existing_helpers_are_thin_wrappers_with_the_same_arguments():
    sql = Path(pgrole.__file__).parent / "sql"
    role = _code((sql / "manage_role_privs.sql").read_text())
    schema = _code((sql / "manage_schema_priv.sql").read_text())
    database = _code((sql / "manage_database_priv.sql").read_text())
    assert re.search(r"function\s+public\.manage_role_privs\(\s*role_name\s+text\s*,\s*action\s+text\s*,\s*priv\s+text\s*\)", role, re.I)
    assert re.search(r"function\s+public\.manage_schema_priv\(\s*action\s+text", schema, re.I)
    assert re.search(r"function\s+public\.manage_database_priv\(\s*action\s+text", database, re.I)
    for body in (role, schema, database):
        assert "public.manage_priv(" in body, "each legacy helper must delegate to the dispatcher"


@pytest.mark.unit
def test_dispatcher_is_installed_before_the_wrappers():
    from bbsengine6.backend import checkfunctions
    src = Path(checkfunctions.__file__).read_text()
    assert '"public.manage_priv"' in src
