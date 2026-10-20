"""can_publish for per-member DM channels.

``member:<moniker>`` has no channel-table row, so the owner check must run
before the lookup. Only the owner may publish; a sysop may not.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.services.channel import ChannelService  # noqa: E402


class TestMemberChannelPublish(unittest.TestCase):
    def setUp(self):
        self.svc = ChannelService(MagicMock())

    def test_owner_may_publish_to_own_channel_without_row(self):
        with patch.object(self.svc, "get_channel", return_value=None) as gc:
            verdict = self.svc.can_publish("member:alice", "alice", is_sysop=False)
        self.assertTrue(verdict["allowed"])
        gc.assert_not_called()

    def test_other_member_denied(self):
        verdict = self.svc.can_publish("member:alice", "bob", is_sysop=False)
        self.assertFalse(verdict["allowed"])

    def test_sysop_cannot_publish_as_member(self):
        verdict = self.svc.can_publish("member:alice", "sysop1", is_sysop=True)
        self.assertFalse(verdict["allowed"])

    def test_non_member_channel_unchanged(self):
        with patch.object(self.svc, "get_channel", return_value=None):
            verdict = self.svc.can_publish("general", "alice", is_sysop=False)
        self.assertEqual(verdict["reason"], "Channel not found")


if __name__ == "__main__":
    unittest.main()
