"""The drop file names exactly the plain-CREATE VIEW views, and nothing that is CREATE OR REPLACE."""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole

SQL = Path(pgrole.__file__).parent / "sql"


def _plain_create_views():
    names = set()
    for f in SQL.glob("*.sql"):
        for m in re.finditer(r"^\s*create\s+view\s+([a-z_.]+)", f.read_text(), re.I | re.M):
            names.add(m.group(1).lower())
    return names


def _dropped():
    text = (SQL / "drop_views_for_recreate.sql").read_text()
    return {m.group(1).lower() for m in re.finditer(r"drop view if exists\s+([a-z_.]+)", text, re.I)}


@pytest.mark.unit
def test_drop_file_covers_every_plain_create_view():
    assert _plain_create_views() <= _dropped(), _plain_create_views() - _dropped()


@pytest.mark.unit
def test_drop_file_does_not_drop_or_replace_views():
    replaced = set()
    for f in SQL.glob("*.sql"):
        for m in re.finditer(r"^\s*create\s+or\s+replace\s+view\s+([a-z_.]+)", f.read_text(), re.I | re.M):
            replaced.add(m.group(1).lower())
    assert not (_dropped() & replaced), _dropped() & replaced


@pytest.mark.unit
def test_drop_file_uses_if_exists():
    text = (SQL / "drop_views_for_recreate.sql").read_text()
    assert all("if exists" in line.lower() for line in text.splitlines() if line.lower().startswith("drop view"))
