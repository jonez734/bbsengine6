"""Named message sources: tagging and group enforcement.

- Member and operator senders keep their existing rules.
- A named source may address only the group prefixes registered for it.
- A named source may never address @everyone.
- store_message / send carry the source through to the DAL insert.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import service  # noqa: E402


class TestResolveSourceRules(unittest.TestCase):
    def setUp(self):
        service.enable()

    def _resolve(self, recipients, source, registered=True):
        with patch("bbsengine6.message.service._resolve_db", return_value="db"), \
             patch("bbsengine6.message.service._make_args", return_value=MagicMock()), \
             patch("bbsengine6.message.service.dal_recipients") as dr, \
             patch("bbsengine6.message.service._source_may_address_group", wraps=service._source_may_address_group) as chk:
            dr.get_group_id_by_name.return_value = 7
            dr.source_may_address_group.return_value = registered
            with patch("bbsengine6.message.service.get_message_group_members", return_value=["alice"]):
                out = service.resolve_recipients(
                    recipients, sender_moniker=None, source=source
                )
        return out, dr

    def test_member_source_unchanged(self):
        out, dr = self._resolve(["@crew"], source="member")
        self.assertEqual(out, ["alice"])
        dr.source_may_address_group.assert_not_called()

    def test_operator_source_unchanged(self):
        out, dr = self._resolve(["@crew"], source="operator")
        self.assertEqual(out, ["alice"])
        dr.source_may_address_group.assert_not_called()

    def test_named_source_registered_expands(self):
        out, dr = self._resolve(["@table:jam"], source="casino.dealer:jam", registered=True)
        self.assertEqual(out, ["alice"])
        dr.source_may_address_group.assert_called_once()

    def test_named_source_unregistered_refused(self):
        with self.assertRaises(PermissionError):
            self._resolve(["@crew"], source="casino.dealer:jam", registered=False)

    def test_named_source_cannot_address_everyone(self):
        with self.assertRaises(PermissionError):
            self._resolve(["@everyone"], source="postoffice")


class TestSourcePlumbing(unittest.TestCase):
    def setUp(self):
        service.enable()

    @patch("bbsengine6.message.service.dal_messages")
    @patch("bbsengine6.message.service.dal_ratelimit")
    @patch("bbsengine6.message.service._make_args", return_value=MagicMock())
    @patch("bbsengine6.message.service._check_blocking_and_ratelimit")
    @patch("bbsengine6.message.service.resolve_recipients", side_effect=lambda r, **k: r)
    def test_store_passes_source_to_dal(self, _res, mock_check, _args, rl, dm):
        mock_check.return_value = (["bob"], True, {"recipients_blocked": [], "recipients_skipped": []})
        rl.try_reserve.return_value = (True, 1)
        dm.store_message_with_recipients.return_value = 9
        service.store_message_with_checks(
            channel="dm", sender_moniker=None, content="x",
            recipient_monikers=["bob"], database="db", source="postoffice",
        )
        self.assertEqual(dm.store_message_with_recipients.call_args.kwargs["source"], "postoffice")

    @patch("bbsengine6.message.service.store_message_with_checks", return_value={"message_id": 3})
    def test_send_forwards_source(self, swc):
        service.send("casino.dealer", ["bob"], "t", sender_moniker=None, source="casino.dealer:jam")
        self.assertEqual(swc.call_args.kwargs["source"], "casino.dealer:jam")


if __name__ == "__main__":
    unittest.main()
