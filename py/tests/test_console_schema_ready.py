"""The console refuses to run against a database whose bootstrap is incomplete.

Regression: on a half-bootstrapped database the console crashed in
member.count with 'relation engine.member does not exist'. It now checks the
member view first and reports the cause.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.console import main as console_main  # noqa: E402


def _conn(exists: bool):
    cur = MagicMock()
    cur.fetchone.return_value = (exists,)
    cur.__enter__ = MagicMock(return_value=cur)
    cur.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


@pytest.mark.unit
def test_schema_ready_true_when_member_view_exists():
    conn, cur = _conn(True)
    assert console_main._schema_ready(conn) is True
    assert "engine.member" in cur.execute.call_args.args[0]


@pytest.mark.unit
def test_schema_ready_false_when_member_view_missing():
    conn, _ = _conn(False)
    assert console_main._schema_ready(conn) is False
