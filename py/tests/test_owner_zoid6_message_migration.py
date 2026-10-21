"""The message-table ownership migration must move every engine message object to zoid6.

The new zoid6-owned SECURITY DEFINER read functions can only read these
relations when zoid6 owns them. Each relation below is currently owned by jam.
"""

import re
from pathlib import Path

import bbsengine6

SQL = Path(bbsengine6.__file__).parent / "sql" / "owner_zoid6_message_migration.sql"

TABLES_AND_VIEWS = [
    "__message",
    "__message_block",
    "__message_group",
    "__message_group_member",
    "__message_rate_limit",
    "__message_recipient",
    "__message_source",
    "__message_type",
    "message",
    "message_blocked",
    "message_unread",
    "message_urgent",
]

SEQUENCES = [
    "__message_block_id_seq",
    "__message_group_id_seq",
    "__message_group_member_id_seq",
    "__message_id_seq",
    "__message_rate_limit_id_seq",
    "__message_recipient_id_seq",
    "__message_type_id_seq",
]


def _text() -> str:
    return "\n".join(
        line for line in SQL.read_text().splitlines()
        if not line.lstrip().startswith("--")
    )


def test_migration_file_exists():
    assert SQL.exists(), f"missing {SQL}"


def test_migration_is_one_transaction():
    text = _text().lower()
    assert "begin;" in text and "commit;" in text


def test_every_message_table_and_view_moves_to_zoid6():
    text = _text()
    for name in TABLES_AND_VIEWS:
        pattern = rf"alter\s+(table|view)\s+engine\.{re.escape(name)}\s+owner\s+to\s+zoid6"
        assert re.search(pattern, text, re.IGNORECASE), f"missing owner move for engine.{name}"


def test_every_message_sequence_moves_to_zoid6():
    text = _text()
    for name in SEQUENCES:
        pattern = rf"alter\s+sequence\s+engine\.{re.escape(name)}\s+owner\s+to\s+zoid6"
        assert re.search(pattern, text, re.IGNORECASE), f"missing owner move for engine.{name}"


def test_no_message_object_is_moved_to_bed():
    assert not re.search(r"owner\s+to\s+bed\b", _text(), re.IGNORECASE)
