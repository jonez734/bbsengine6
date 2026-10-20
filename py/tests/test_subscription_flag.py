"""The push-subscription flag is set on success and read by getch.

Without this, getch silently falls back to DB polling even when bed pushes are
active (the lookup raises and is swallowed).
"""

import asyncio
import importlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.startup import message_subscription as ms  # noqa: E402

g = importlib.import_module("bbsengine6.io.getch")


class TestSubscriptionFlag(unittest.TestCase):
    def setUp(self):
        ms._subscribed_monikers.clear()

    def test_flag_set_on_successful_subscribe(self):
        with patch.object(ms, "_probe", return_value=True), \
             patch.object(ms, "_resolve_token", return_value="tok"), \
             patch.object(ms, "_get_connection", return_value=object()), \
             patch("bed.client.authservice.BedAuthServiceClient") as ac, \
             patch("bed.client.messageservice.get_message_client") as gmc:
            ac.return_value.reconnect = AsyncMock(return_value={"ok": True, "moniker": "alice"})
            gmc.return_value.subscribe = AsyncMock(return_value={"ok": True})
            asyncio.run(ms.subscribe_to_bed(SimpleNamespace(debug=False, token_file="/x"), "alice"))
        self.assertTrue(ms.is_subscribed("alice"))
        self.assertTrue(g._push_subscribed("alice"))

    def test_getch_sees_flag_for_its_moniker_only(self):
        ms._mark_subscribed("alice", True)
        self.assertTrue(g._push_subscribed("alice"))
        self.assertFalse(g._push_subscribed("bob"))
        self.assertFalse(g._push_subscribed(None))

    def test_flag_cleared_when_marked_inactive(self):
        ms._mark_subscribed("alice", True)
        ms._mark_subscribed("alice", False)
        self.assertFalse(g._push_subscribed("alice"))


if __name__ == "__main__":
    unittest.main()
