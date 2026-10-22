"""The owner migration moves the bank schema objects to zoid6, so zoid6-owned definer functions can read them."""

import re
from pathlib import Path

import bbsengine6

SQL = Path(bbsengine6.__file__).parent / "sql" / "owner_zoid6_migration.sql"

TABLES = ["__account", "__transaction", "__transfer"]
VIEWS = ["account", "transaction", "transfer"]


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


def test_bank_tables_move_to_zoid6():
    t = _code(SQL.read_text())
    for name in TABLES:
        assert re.search(rf"alter\s+table\s+bank\.{re.escape(name)}\s+owner\s+to\s+zoid6", t, re.IGNORECASE), name


def test_bank_views_move_to_zoid6():
    t = _code(SQL.read_text())
    for name in VIEWS:
        assert re.search(rf"alter\s+view\s+bank\.{re.escape(name)}\s+owner\s+to\s+zoid6", t, re.IGNORECASE), name


def test_bank_sequences_move_to_zoid6():
    t = _code(SQL.read_text())
    for name in ["__account_id_seq", "__transaction_id_seq", "__transfer_id_seq"]:
        assert re.search(rf"alter\s+sequence\s+bank\.{re.escape(name)}\s+owner\s+to\s+zoid6", t, re.IGNORECASE), name
