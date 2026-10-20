"""@everyone is restricted to configured roles (default: sysop).

Covers: the default blocks a non-sysop sender, a sysop is allowed, operator
calls with no sender are allowed, a denied broadcast stores nothing and
reports the reason, and configure() replaces the role list.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.message import service  # noqa: E402


class TestEveryonePolicy(unittest.TestCase):
    def setUp(self):
        service.enable()
        service.configure(everyone_allowed_roles=["sysop"])

    def tearDown(self):
        service.configure(everyone_allowed_roles=["sysop"])

    def _patches(self, issysop_value):
        """Patch the DB-facing pieces resolve_recipients touches."""
        return [
            patch("bbsengine6.message.service._resolve_db", return_value="db"),
            patch("bbsengine6.message.service._make_args", return_value=MagicMock()),
            patch("bbsengine6.message.service.dal_recipients"),
            patch("bbsengine6.member.lib.issysop", return_value=issysop_value),
        ]

    def _run(self, issysop_value, sender):
        ps = self._patches(issysop_value)
        mocks = [p.start() for p in ps]
        try:
            dal = mocks[2]
            dal.list_all_approved_member_monikers.return_value = ["alice", "bob"]
            return service.resolve_recipients(["@everyone"], sender_moniker=sender), dal
        finally:
            for p in ps:
                p.stop()

    def test_non_sysop_is_denied(self):
        with self.assertRaises(PermissionError):
            self._run(issysop_value=False, sender="alice")

    def test_sysop_is_allowed(self):
        out, dal = self._run(issysop_value=True, sender="root")
        self.assertEqual(out, ["alice", "bob"])
        dal.list_all_approved_member_monikers.assert_called_once()

    def test_operator_call_without_sender_is_allowed(self):
        out, _ = self._run(issysop_value=False, sender=None)
        self.assertEqual(out, ["alice", "bob"])

    def test_denied_broadcast_stores_nothing_and_reports_reason(self):
        with patch("bbsengine6.message.service.store_message_with_checks") as _:
            pass
        with patch("bbsengine6.message.service._resolve_db", return_value="db"), \
             patch("bbsengine6.message.service._make_args", return_value=MagicMock()), \
             patch("bbsengine6.message.service.dal_messages") as dm, \
             patch("bbsengine6.message.service.dal_ratelimit"), \
             patch("bbsengine6.member.lib.issysop", return_value=False):
            out = service.store_message_with_checks(
                channel="dm", sender_moniker="alice", content="hi",
                recipient_monikers=["@everyone"], database="db",
            )
        self.assertEqual(out["message_id"], 0)
        self.assertIn("sysop", out["denied_reason"])
        dm.store_message_with_recipients.assert_not_called()

    def test_configure_replaces_roles(self):
        service.configure(everyone_allowed_roles=[])
        self.assertEqual(service._everyone_allowed_roles, [])
        # With no roles configured, even a sysop is denied.
        with self.assertRaises(PermissionError):
            self._run(issysop_value=True, sender="root")

    def test_configure_none_keeps_current(self):
        service.configure(everyone_allowed_roles=["sysop"])
        service.configure(everyone_allowed_roles=None)
        self.assertEqual(service._everyone_allowed_roles, ["sysop"])


if __name__ == "__main__":
    unittest.main()
