"""The member-flag tables must be owned by zoid6.

engine.checkmemberflag runs inside bed's zoid6-owned SECURITY DEFINER wrapper.
The wrapper runs as zoid6, so zoid6 must own the flag tables it reads. Neither
owner migration moved them, so they stayed owned by jam.
"""

import re
from pathlib import Path

import bbsengine6

SQL = Path(bbsengine6.__file__).parent / "sql" / "owner_zoid6_migration.sql"


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


def test_member_flag_table_moves_to_zoid6():
    assert re.search(r"alter\s+table\s+engine\.member_flag\s+owner\s+to\s+zoid6", _code(SQL.read_text()), re.IGNORECASE)


def test_map_member_flag_table_moves_to_zoid6():
    assert re.search(r"alter\s+table\s+engine\.map_member_flag\s+owner\s+to\s+zoid6", _code(SQL.read_text()), re.IGNORECASE)


def test_flag_objects_not_moved_to_bed():
    assert not re.search(r"owner\s+to\s+bed\b", _code(SQL.read_text()), re.IGNORECASE)


def test_member_table_and_view_move_to_zoid6():
    text = SQL.read_text()
    assert re.search(r"alter\s+table\s+engine\.__member\s+owner\s+to\s+zoid6", text, re.IGNORECASE)
    assert re.search(r"alter\s+view\s+engine\.member\s+owner\s+to\s+zoid6", text, re.IGNORECASE)
