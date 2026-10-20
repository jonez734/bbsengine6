"""list_pending pagination and age limit.

- get_pending_page clamps limit to 1..PENDING_PAGE_MAX.
- the cursor is passed through to the DAL; the DAL orders by (datestamp, id).
- configure(pending_max_age_days=...) reaches the DAL as max_age_days.
- configure rejects a negative age.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import service  # noqa: E402


class TestPendingPage(unittest.TestCase):
    def setUp(self):
        service.enable()
        service.configure(pending_max_age_days=0)

    def tearDown(self):
        service.configure(pending_max_age_days=0)

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_messages")
    def test_limit_is_clamped_high(self, dal, _db, _args):
        dal.list_pending_page.return_value = []
        service.get_pending_page("alice", limit=10_000)
        self.assertEqual(dal.list_pending_page.call_args[0][2], service.PENDING_PAGE_MAX)

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_messages")
    def test_limit_is_clamped_low(self, dal, _db, _args):
        dal.list_pending_page.return_value = []
        service.get_pending_page("alice", limit=0)
        self.assertEqual(dal.list_pending_page.call_args[0][2], 1)

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_messages")
    def test_cursor_passed_through(self, dal, _db, _args):
        dal.list_pending_page.return_value = []
        cursor = ("2026-10-01 12:00:00", 42)
        service.get_pending_page("alice", limit=20, before=cursor)
        self.assertEqual(dal.list_pending_page.call_args.kwargs["before"], cursor)

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_messages")
    def test_ttl_reaches_dal(self, dal, _db, _args):
        dal.list_pending_page.return_value = []
        service.configure(pending_max_age_days=14)
        service.get_pending_page("alice")
        self.assertEqual(dal.list_pending_page.call_args.kwargs["max_age_days"], 14)

    def test_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            service.configure(pending_max_age_days=-1)


if __name__ == "__main__":
    unittest.main()
