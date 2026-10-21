"""The message INSERT must pass one parameter per placeholder.

A mismatch (8 placeholders, 7 parameters) breaks every real message insert.
The DAL is otherwise mocked in unit tests, so this checks the SQL and its
parameter tuple directly, using a recording cursor.
"""

import inspect
import os
import re
import sys
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message.dal import messages as dal  # noqa: E402


class _Cursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.calls.append((sql, params))

    def fetchone(self):
        return (1,)

    def fetchall(self):
        return []


class TestInsertParameterCount(unittest.TestCase):
    def test_message_insert_placeholders_match_parameters(self):
        cur = _Cursor()
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__.return_value = conn
        conn.__exit__.return_value = False

        @contextmanager
        def fake_ctx(args, pool=None):
            yield conn

        with patch.object(dal, "_connect_ctx", fake_ctx):
            dal.store_message_with_recipients(
                args=None,
                channel="dm",
                sender_moniker="alice",
                content="hi",
                data=None,
                urgency="ROUTINE",
                template=None,
                template_vars=None,
                allowed_recipients=["bob"],
                source="member",
            )

        sql, params = cur.calls[0]
        placeholders = len(re.findall(r"%s", sql))
        self.assertEqual(
            placeholders, len(params),
            f"{placeholders} placeholders but {len(params)} parameters",
        )
        self.assertIn("source", sql)
        self.assertEqual(params[-1], "member")


if __name__ == "__main__":
    unittest.main()
