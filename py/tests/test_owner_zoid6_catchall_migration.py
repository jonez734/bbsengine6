"""The owner migration moves every engine and bank object that zoid6 does not own.

The live catalog had objects the repo did not list (for example __folder, __session,
pgrole, __invite, and several functions). A catch-all block finds them by catalog query,
so a future object created under another owner is also moved.
"""

import re
from pathlib import Path

import pytest

import bbsengine6

SQL = Path(bbsengine6.__file__).parent / "sql" / "owner_zoid6_migration.sql"


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


def _catchall() -> str:
    t = _code(SQL.read_text())
    m = re.search(r"do\s+\$owner\$.*?\$owner\$\s*;", t, re.IGNORECASE | re.DOTALL)
    assert m, "catch-all DO block missing"
    return m.group(0)


@pytest.mark.unit
def test_catchall_block_exists_and_is_idempotent_by_catalog_filter():
    block = _catchall()
    assert "pg_get_userbyid(c.relowner) <> 'zoid6'" in block
    assert "pg_get_userbyid(p.proowner) <> 'zoid6'" in block


@pytest.mark.unit
def test_catchall_covers_engine_and_bank_schemas():
    block = _catchall()
    assert re.search(r"in\s*\(\s*'engine'\s*,\s*'bank'\s*\)", block, re.IGNORECASE)


@pytest.mark.unit
@pytest.mark.parametrize("kind,stmt", [("table", "alter table"), ("view", "alter view"), ("sequence", "alter sequence")])
def test_catchall_alters_each_relation_kind(kind, stmt):
    block = _catchall()
    assert re.search(rf"execute\s+format\('{stmt} %I\.%I owner to zoid6'", block, re.IGNORECASE), kind


@pytest.mark.unit
def test_catchall_alters_functions():
    assert re.search(r"execute\s+format\('alter function %I\.%I\(%s\) owner to zoid6'", _catchall(), re.IGNORECASE)


@pytest.mark.unit
def test_catchall_never_hands_objects_to_bed():
    assert not re.search(r"owner\s+to\s+bed\b", _code(SQL.read_text()), re.IGNORECASE)
