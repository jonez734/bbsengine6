"""Regression tests for message Step 3b-ii.

- cache: the unread lock exists at import time (no lazy creation race).
- send(): should_persist=False stores nothing; unknown kwargs raise TypeError.
- resolve_recipients: nested @group references expand; a cycle terminates.
- rate limit: a slot is reserved only for a stored message and is released
  when the insert fails.

All run without a database; DAL calls are mocked.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import cache, service  # noqa: E402


class TestCacheLock(unittest.TestCase):
    def test_lock_exists_at_import_time(self):
        # Previously _local_lock was None until first use, and two threads
        # could each create a different Lock.
        self.assertIsNotNone(cache._local_lock)
        self.assertIs(cache._ensure_lock(), cache._local_lock)
        self.assertIs(cache._ensure_lock(), cache._ensure_lock())


class TestSendHardening(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service.store_message")
    def test_should_persist_false_stores_nothing(self, mock_store):
        out = service.send(
            "casino_kick", ["alice"], "hi", should_persist=False
        )
        self.assertEqual(out, 0)
        mock_store.assert_not_called()

    @patch("bbsengine6.message.service.store_message", return_value=5)
    def test_should_persist_true_stores(self, mock_store):
        out = service.send("casino_kick", ["alice"], "hi")
        self.assertEqual(out, 5)
        mock_store.assert_called_once()

    @patch("bbsengine6.message.service.store_message")
    def test_unknown_kwarg_raises(self, mock_store):
        with self.assertRaises(TypeError):
            service.send("casino_kick", ["alice"], "hi", recipent="bob")
        mock_store.assert_not_called()


class TestNestedGroups(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_recipients")
    @patch("bbsengine6.message.service.get_message_group_members")
    def test_nested_group_is_expanded(self, mock_members, mock_dal, _db, _args):
        mock_dal.get_group_id_by_name.side_effect = lambda a, name: {"outer": 1, "inner": 2}[name]
        mock_members.side_effect = lambda gid, database=None: {
            1: ["alice", "@inner"],
            2: ["bob", "carol"],
        }[gid]

        out = service.resolve_recipients(["@outer"])

        self.assertEqual(out, ["alice", "bob", "carol"])

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._resolve_db", return_value="db")
    @patch("bbsengine6.message.service.dal_recipients")
    @patch("bbsengine6.message.service.get_message_group_members")
    def test_cycle_terminates(self, mock_members, mock_dal, _db, _args):
        mock_dal.get_group_id_by_name.side_effect = lambda a, name: {"a": 1, "b": 2}[name]
        mock_members.side_effect = lambda gid, database=None: {
            1: ["x", "@b"],
            2: ["y", "@a"],
        }[gid]

        out = service.resolve_recipients(["@a"])

        self.assertEqual(sorted(out), ["x", "y"])


class TestRateReservation(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service.dal_ratelimit")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_failed_insert_releases_slot(self, _res, mock_check, mock_dal, _args, mock_rl):
        mock_check.return_value = (["carol"], True, {"recipients_blocked": [], "recipients_skipped": []})
        mock_rl.try_reserve.return_value = (True, 4)
        mock_dal.store_message_with_recipients.side_effect = RuntimeError("db down")

        with self.assertRaises(RuntimeError):
            service.store_message_with_checks(
                channel="dm", sender_moniker="alice", content="hi",
                recipient_monikers=["carol"], database="db",
            )

        mock_rl.release.assert_called_once()

    @patch("bbsengine6.message.service.dal_ratelimit")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_all_blocked_does_not_reserve(self, _res, mock_check, mock_dal, _args, mock_rl):
        mock_check.return_value = ([], True, {"recipients_blocked": ["bob"], "recipients_skipped": []})

        out = service.store_message_with_checks(
            channel="dm", sender_moniker="alice", content="hi",
            recipient_monikers=["bob"], database="db",
        )

        self.assertEqual(out["message_id"], 0)
        mock_rl.try_reserve.assert_not_called()
        mock_dal.store_message_with_recipients.assert_not_called()

    @patch("bbsengine6.message.service.dal_ratelimit")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_over_limit_refuses_without_insert(self, _res, mock_check, mock_dal, _args, mock_rl):
        mock_check.return_value = (["carol"], True, {"recipients_blocked": [], "recipients_skipped": []})
        mock_rl.try_reserve.return_value = (False, 0)

        out = service.store_message_with_checks(
            channel="dm", sender_moniker="alice", content="hi",
            recipient_monikers=["carol"], database="db",
        )

        self.assertFalse(out["rate_limit_ok"])
        self.assertEqual(out["message_id"], 0)
        mock_dal.store_message_with_recipients.assert_not_called()


if __name__ == "__main__":
    unittest.main()
