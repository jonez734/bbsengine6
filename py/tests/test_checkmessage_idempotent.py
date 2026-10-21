"""checkmessage must not re-run a SQL file that creates several tables.

Regression: a file with several plain CREATE TABLE statements was re-run when
one of its tables was missing, and failed with "relation already exists" on
the sibling table it had already created.
"""

import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.backend import checkmessage  # noqa: E402

SQL_DIR = Path(__file__).resolve().parents[1] / "src" / "bbsengine6" / "sql"


def _tables_created(sql_file: str):
    """Tables and views a file creates (both are classes to checkmessage)."""
    text = (SQL_DIR / sql_file).read_text()
    return re.findall(
        r"^create (?:or replace )?(?:table|view)(?: if not exists)? (\S+)",
        text, re.M | re.I,
    )


@pytest.mark.unit
def test_each_file_listed_creates_the_tables_mapped_to_it():
    """The class map and the SQL files agree: every mapped table is created by its file."""
    for table, sql_file in checkmessage.classlist:
        assert table in _tables_created(sql_file), f"{table} not created by {sql_file}"


@pytest.mark.unit
def test_no_sql_file_is_imported_twice_in_one_pass():
    imports = []

    def fake_importsql(args, sql, conn=None, rollback=True):
        imports.append(sql)
        return True

    # Every class reports missing, so every file would be imported once per class.
    with patch.object(checkmessage, "classexists", return_value=False), \
         patch.object(checkmessage, "typeexists", return_value=False), \
         patch.object(checkmessage.database, "importsql", side_effect=fake_importsql), \
         patch.object(checkmessage.database, "cursor") as cur_ctx, \
         patch.object(checkmessage.lib, "_ensure_autocommit_off"), \
         patch.object(checkmessage.lib, "retry_on_transient", side_effect=lambda f: f()):
        cur_ctx.return_value.__enter__.return_value = MagicMock()
        conn = MagicMock()
        checkmessage.main(MagicMock(), conn=conn)

    assert len(imports) == len(set(imports)), f"files imported more than once: {imports}"
