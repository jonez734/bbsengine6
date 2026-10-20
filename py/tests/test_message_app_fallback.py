"""Apps without a bed login fall back to polling and open no socket."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.startup import message_subscription as ms  # noqa: E402


def _args(tmp_token_file=None, debug=False):
    return SimpleNamespace(
        debug=debug, token=None, token_file=tmp_token_file,
        bed_host="127.0.0.1", bed_port=8765,
    )


class TestAppFallback(unittest.TestCase):
    def setUp(self):
        ms._debug_notice_emitted = False
        ms._subscribed_monikers.clear()

    def test_no_bed_no_socket_no_subscription(self):
        with patch.object(ms, "_probe", return_value=False), \
             patch("bed.client.get_bed_connection") as singleton:
            ok = asyncio.run(ms.subscribe_to_bed(_args(), "alice"))
        self.assertFalse(ok)
        singleton.assert_not_called()
        self.assertFalse(ms.is_subscribed("alice"))

    def test_bed_up_but_no_token_no_socket(self):
        with patch.object(ms, "_probe", return_value=True), \
             patch.object(ms, "_resolve_token", return_value=""), \
             patch("bed.client.get_bed_connection") as singleton:
            ok = asyncio.run(ms.subscribe_to_bed(_args(), "alice"))
        self.assertFalse(ok)
        singleton.assert_not_called()
        self.assertFalse(ms.is_subscribed("alice"))

    def test_failed_subscribe_is_not_marked_subscribed(self):
        with patch.object(ms, "_probe", return_value=True), \
             patch.object(ms, "_resolve_token", return_value="tok"), \
             patch.object(ms, "_get_connection", return_value=object()), \
             patch("bed.client.authservice.BedAuthServiceClient") as ac, \
             patch("bed.client.messageservice.get_message_client") as gmc:
            from unittest.mock import AsyncMock
            ac.return_value.reconnect = AsyncMock(return_value={"ok": False, "code": "token_expired"})
            ok = asyncio.run(ms.subscribe_to_bed(_args(), "alice"))
        self.assertFalse(ok)
        self.assertFalse(ms.is_subscribed("alice"))


class TestCasinoPath(unittest.TestCase):
    """Casino logs in through bed.client.get_bed_connection (singleton).

    The startup subscribe runs with no caller handle, so it uses that same
    singleton and is the owner of it (it may write rotated tokens).
    """

    def setUp(self):
        ms._subscribed_monikers.clear()

    def test_no_handle_uses_singleton_and_owns_it(self):
        from unittest.mock import AsyncMock
        singleton_conn = object()
        with patch.object(ms, "_probe", return_value=True), \
             patch.object(ms, "_resolve_token", return_value="tok"), \
             patch("bed.client.get_bed_connection", return_value=singleton_conn) as gbc, \
             patch("bed.client.authservice.BedAuthServiceClient") as ac, \
             patch("bed.client.messageservice.get_message_client") as gmc:
            ac.return_value.reconnect = AsyncMock(return_value={"ok": True, "moniker": "alice"})
            gmc.return_value.subscribe = AsyncMock(return_value={"ok": True})
            ok = asyncio.run(ms.subscribe_to_bed(_args(tmp_token_file="/x"), "alice"))
        self.assertTrue(ok)
        gbc.assert_called_once()
        self.assertTrue(gmc.call_args.kwargs["owner"])
        self.assertTrue(ms.is_subscribed("alice"))


class TestSuppliedHandle(unittest.TestCase):
    """An app that passes bed= keeps ownership; this process does not write tokens."""

    def setUp(self):
        ms._subscribed_monikers.clear()

    def test_supplied_handle_is_not_owner(self):
        from unittest.mock import AsyncMock
        handle = object()
        with patch.object(ms, "_probe", return_value=True), \
             patch.object(ms, "_resolve_token", return_value="tok"), \
             patch("bed.client.get_bed_connection") as gbc, \
             patch("bed.client.authservice.BedAuthServiceClient") as ac, \
             patch("bed.client.messageservice.get_message_client") as gmc:
            ac.return_value.reconnect = AsyncMock(return_value={"ok": True, "moniker": "alice"})
            gmc.return_value.subscribe = AsyncMock(return_value={"ok": True})
            ok = asyncio.run(ms.subscribe_to_bed(_args(tmp_token_file="/x"), "alice", bed=handle))
        self.assertTrue(ok)
        gbc.assert_not_called()
        self.assertFalse(gmc.call_args.kwargs["owner"])


if __name__ == "__main__":
    unittest.main()
