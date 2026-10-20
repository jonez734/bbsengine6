"""Regression tests for message orphan rows and on-connect redelivery.

- store_message_with_checks must not insert a message when recipients were
  requested but every one was blocked, and must report message_id=0.
- deliver_pending_on_connect must query only never-delivered rows and mark
  them in one batch, so already-delivered rows are not pushed again.

These mock the DAL, so they run without a database.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import service  # noqa: E402


class TestNoOrphanOnAllBlocked(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service.record_message_sent")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_all_recipients_blocked_does_not_insert(
        self, _resolve, mock_check, mock_dal, _args, _rec
    ):
        mock_check.return_value = (
            [],
            True,
            {"recipients_blocked": ["bob"], "recipients_skipped": []},
        )

        result = service.store_message_with_checks(
            channel="dm",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob"],
            database="db",
        )

        mock_dal.store_message_with_recipients.assert_not_called()
        self.assertEqual(result["message_id"], 0)
        self.assertEqual(result["recipients_stored"], [])
        self.assertEqual(result["recipients_blocked"], ["bob"])

    @patch("bbsengine6.message.service.dal_ratelimit")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_some_allowed_still_inserts(
        self, _resolve, mock_check, mock_dal, _args, mock_rl
    ):
        mock_rl.try_reserve.return_value = (True, 9)
        mock_check.return_value = (
            ["carol"],
            True,
            {"recipients_blocked": ["bob"], "recipients_skipped": []},
        )
        mock_dal.store_message_with_recipients.return_value = 42

        result = service.store_message_with_checks(
            channel="dm",
            sender_moniker="alice",
            content="hi",
            recipient_monikers=["bob", "carol"],
            database="db",
        )

        mock_dal.store_message_with_recipients.assert_called_once()
        self.assertEqual(result["message_id"], 42)
        self.assertEqual(result["recipients_stored"], ["carol"])


class TestOnConnectRedelivery(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    def test_queries_only_undelivered_and_batches_mark(self, mock_dal, _args):
        mock_dal.list_undelivered_for_recipient.return_value = [
            {"id": 7, "channel": "dm", "content": "a"},
            {"id": 9, "channel": "dm", "content": "b"},
        ]

        out = service.deliver_pending_on_connect("bob", database="db")

        self.assertEqual([m["id"] for m in out], [7, 9])
        # Uses the pending-only query, not the pending+delivered list.
        mock_dal.list_undelivered_for_recipient.assert_called_once()
        mock_dal.list_pending_for_recipient.assert_not_called()
        # One batched UPDATE, not one per message.
        mock_dal.mark_delivered_batch.assert_called_once()
        self.assertEqual(mock_dal.mark_delivered_batch.call_args[0][1], [7, 9])
        self.assertEqual(mock_dal.mark_delivered.call_count, 0)

    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service.dal_messages")
    def test_empty_inbox_skips_update(self, mock_dal, _args):
        mock_dal.list_undelivered_for_recipient.return_value = []
        self.assertEqual(service.deliver_pending_on_connect("bob", database="db"), [])
        mock_dal.mark_delivered_batch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
