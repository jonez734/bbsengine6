"""engine.__actionlog (table) and engine.actionlog (view) are separate files, loaded by startup.

The login log is append-only: no role gets update or delete on the table, and no role gets
direct insert either, since writes go through the single writer function (phase 2).
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkclasses

SQL = Path(pgrole.__file__).parent / "sql"
TABLE = SQL / "actionlog.sql"
VIEW = SQL / "actionlog_view.sql"


@pytest.mark.unit
def test_table_and_view_are_separate_files():
    assert TABLE.is_file() and VIEW.is_file()


@pytest.mark.unit
def test_table_file_holds_the_table_and_not_the_view():
    text = TABLE.read_text().lower()
    assert "create table if not exists engine.__actionlog" in text
    assert "create or replace view engine.actionlog" not in text
    assert "create view engine.actionlog" not in text


@pytest.mark.unit
def test_view_file_holds_the_view_and_not_the_table():
    text = VIEW.read_text().lower()
    assert "create or replace view engine.actionlog" in text
    assert "create table" not in text


@pytest.mark.unit
def test_view_reads_the_table_and_uses_the_loginid_join():
    text = VIEW.read_text().lower()
    assert "engine.__actionlog" in text
    assert "currentmember.loginid = current_user" in text


@pytest.mark.unit
def test_both_are_registered_table_first():
    names = [cls for cls, _ in checkclasses.classlist]
    assert ("engine.__actionlog", "actionlog.sql") in checkclasses.classlist
    assert ("engine.actionlog", "actionlog_view.sql") in checkclasses.classlist
    assert names.index("engine.__actionlog") < names.index("engine.actionlog")


@pytest.mark.unit
@pytest.mark.parametrize("path", [TABLE, VIEW])
def test_files_have_no_psql_meta_commands(path):
    bad = [l for l in path.read_text().splitlines() if re.match(r"^\s*\\", l)]
    assert bad == [], bad


@pytest.mark.unit
def test_table_grants_no_update_or_delete_to_any_role():
    text = TABLE.read_text().lower()
    assert not re.search(r"grant\s+[^;]*\b(update|delete|all)\b[^;]*on\s+engine\.__actionlog", text), text
    assert "grant all" not in text


@pytest.mark.unit
def test_table_is_idempotent():
    text = TABLE.read_text().lower()
    assert "create table if not exists" in text


@pytest.mark.unit
def test_moniker_column_matches_member_moniker_type():
    """engine.__member.moniker is citext. A foreign key needs the same type, so the log's
    moniker column must be citext too, or startup fails with DatatypeMismatch."""
    text = TABLE.read_text().lower()
    assert re.search(r"moniker\s+citext\b", text), "moniker must be citext to match engine.__member"
    assert not re.search(r"moniker\s+text\b", text), "moniker must not be text"
