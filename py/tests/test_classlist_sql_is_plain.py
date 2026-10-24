"""Every file in checkclasses.classlist must be plain SQL that importsql can run.

importsql sends the file to the server as-is, so psql meta-commands (\\echo, \\i) fail,
and a CREATE INDEX without IF NOT EXISTS fails when startup reruns over an existing
database. Both broke the startup check after the view registration change.
"""

import re
from pathlib import Path

import pytest

from bbsengine6 import pgrole
from bbsengine6.backend import checkclasses

SQL = Path(pgrole.__file__).parent / "sql"


def _classlist_files():
    return sorted({f for _, f in checkclasses.classlist})


@pytest.mark.unit
@pytest.mark.parametrize("name", _classlist_files())
def test_classlist_file_has_no_psql_meta_commands(name):
    text = (SQL / name).read_text()
    bad = [l for l in text.splitlines() if re.match(r"^\s*\\", l)]
    assert bad == [], f"{name}: {bad[:3]}"


@pytest.mark.unit
@pytest.mark.parametrize("name", _classlist_files())
def test_classlist_file_indexes_are_idempotent(name):
    text = (SQL / name).read_text()
    bad = [
        l for l in text.splitlines()
        if re.match(r"^\s*(create|CREATE)\s+(unique\s+)?(index|INDEX)\s", l)
        and not re.search(r"if\s+not\s+exists", l, re.I)
        and not l.lstrip().startswith("--")
    ]
    assert bad == [], f"{name}: {bad[:3]}"
