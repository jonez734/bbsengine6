"""subscribe_to_bed entry point: probe, token, identity check, handle choice."""

import asyncio
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.startup import message_subscription as ms  # noqa: E402


def _args(**kw):
    base = dict(debug=False, token_file=None, token=None,
                bed_host="127.0.0.1", bed_port=8765)
    base.update(kw)
    return SimpleNamespace(**base)


class TestSubscribeEntry(unittest.TestCase):
    def setUp(self):
        ms._debug_notice_emitted = False

    def _run(self, args, moniker="alice", **kwargs):
        return asyncio.run(ms.subscribe_to_bed(args, moniker, **kwargs))

    @patch("bbsengine6.startup.message_subscription._probe", return_value=False)
    def test_no_bed_returns_false(self, _p):
        self.assertFalse(self._run(_args(token="t")))

    @patch("bbsengine6.startup.message_subscription._probe", return_value=True)
    @patch("bbsengine6.startup.message_subscription._resolve_token", return_value="")
    def test_no_token_returns_false(self, _t, _p):
        self.assertFalse(self._run(_args()))

    @patch("bbsengine6.startup.message_subscription._probe", return_value=True)
    @patch("bbsengine6.startup.message_subscription._resolve_token", return_value="tok")
    @patch("bbsengine6.startup.message_subscription._get_connection", return_value=None)
    def test_no_connection_returns_false(self, _c, _t, _p):
        self.assertFalse(self._run(_args()))

    def test_mismatched_bound_moniker_refused(self):
        conn = MagicMock(name="conn")
        auth = MagicMock()
        auth.reconnect = AsyncMock(return_value={"ok": True, "moniker": "mallory", "token": "new"})
        client = MagicMock()
        client.subscribe = AsyncMock(return_value={"ok": True})
        with patch("bbsengine6.startup.message_subscription._probe", return_value=True), \
             patch("bbsengine6.startup.message_subscription._resolve_token", return_value="tok"), \
             patch("bbsengine6.startup.message_subscription._get_connection", return_value=conn), \
             patch("bed.client.authservice.BedAuthServiceClient", return_value=auth), \
             patch("bed.client.messageservice.get_message_client", return_value=client):
            self.assertFalse(self._run(_args(), moniker="alice"))
        client.subscribe.assert_not_called()

    def test_matching_bound_moniker_subscribes(self):
        conn = MagicMock(name="conn")
        auth = MagicMock()
        auth.reconnect = AsyncMock(return_value={"ok": True, "moniker": "alice", "token": "new"})
        client = MagicMock()
        client.subscribe = AsyncMock(return_value={"ok": True})
        with patch("bbsengine6.startup.message_subscription._probe", return_value=True), \
             patch("bbsengine6.startup.message_subscription._resolve_token", return_value="tok"), \
             patch("bbsengine6.startup.message_subscription._get_connection", return_value=conn), \
             patch("bed.client.authservice.BedAuthServiceClient", return_value=auth), \
             patch("bed.client.messageservice.get_message_client", return_value=client):
            self.assertTrue(self._run(_args(), moniker="alice"))
        client.subscribe.assert_awaited_once_with("alice")

    def test_supplied_handle_used_not_singleton(self):
        handle = MagicMock(name="handle")
        with patch("bbsengine6.startup.message_subscription._probe", return_value=True), \
             patch("bbsengine6.startup.message_subscription._resolve_token", return_value="tok"), \
             patch("bed.client.get_bed_connection") as singleton, \
             patch("bed.client.authservice.BedAuthServiceClient") as ac, \
             patch("bed.client.messageservice.get_message_client") as gmc:
            ac.return_value.reconnect = AsyncMock(return_value={"ok": True, "moniker": "alice"})
            gmc.return_value.subscribe = AsyncMock(return_value={"ok": True})
            self._run(_args(), moniker="alice", bed=handle)
        singleton.assert_not_called()
        ac.assert_called_once_with(handle)

    @patch("bbsengine6.startup.message_subscription.io.echo")
    @patch("bbsengine6.startup.message_subscription._probe", return_value=False)
    def test_debug_line_only_when_debug_and_once(self, _p, echo):
        self._run(_args(debug=False))
        self._run(_args(debug=True))
        self._run(_args(debug=True))
        self.assertEqual(echo.call_count, 1)

    @patch("bbsengine6.startup.message_subscription.io.echo")
    @patch("bbsengine6.startup.message_subscription._probe", return_value=False)
    def test_no_debug_no_line(self, _p, echo):
        self._run(_args(debug=False))
        echo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
