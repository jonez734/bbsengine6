"""The owner migration moves the channel and subscribe objects to zoid6.

engine.__channel is referenced by engine.__member (createdby). Deleting a member runs
an internal UPDATE on __channel as its owner, so an owner without engine access makes the
delete fail. These objects are created by sql/channel.sql and sql/subscribe.sql.
"""

import re
from pathlib import Path

import pytest

import bbsengine6

SQL = Path(bbsengine6.__file__).parent / "sql" / "owner_zoid6_migration.sql"

TABLES = ["__channel", "__channel_announcer", "subscribe_blurb", "subscribe_sig"]
VIEWS = ["channel"]
SEQUENCES = ["__channel_id_seq", "__channel_announcer_id_seq"]  # subscribe_* have no serial column


def _code(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("--"))


@pytest.mark.unit
@pytest.mark.parametrize("name", TABLES)
def test_channel_table_moves_to_zoid6(name):
    assert re.search(rf"alter\s+table\s+engine\.{re.escape(name)}\s+owner\s+to\s+zoid6", _code(SQL.read_text()), re.IGNORECASE), name


@pytest.mark.unit
@pytest.mark.parametrize("name", VIEWS)
def test_channel_view_moves_to_zoid6(name):
    assert re.search(rf"alter\s+view\s+engine\.{re.escape(name)}\s+owner\s+to\s+zoid6", _code(SQL.read_text()), re.IGNORECASE), name


@pytest.mark.unit
@pytest.mark.parametrize("name", SEQUENCES)
def test_channel_sequence_moves_to_zoid6(name):
    assert re.search(rf"alter\s+sequence\s+engine\.{re.escape(name)}\s+owner\s+to\s+zoid6", _code(SQL.read_text()), re.IGNORECASE), name
