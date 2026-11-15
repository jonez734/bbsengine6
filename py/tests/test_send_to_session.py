"""WebSocketServer.send_to_session sends a message to the one live socket bound to a session id.

A casino table sends each seated player their own game state; the transport finds the socket by the
session id it stamped on the connection. A session with no live socket is a no-op, not an error.
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from bbsengine6.net.transport import WebSocketServer


class TestSendToSession(unittest.TestCase):
    def _server_with(self, *sockets):
        server = WebSocketServer(host="127.0.0.1", port=0)
        clients = server._clients.setdefault("default", set())
        clients.update(sockets)
        return server

    def _socket(self, session_id):
        ws = MagicMock(name=f"ws_{session_id}")
        ws._bbsengine6_session_id = session_id
        ws.send = AsyncMock()
        return ws

    def test_sends_only_to_the_socket_bound_to_the_session(self):
        a, b = self._socket(1), self._socket(2)
        server = self._server_with(a, b)

        asyncio.run(server.send_to_session(2, {"type": "game_state", "phase": "playing"}))

        b.send.assert_awaited_once()
        a.send.assert_not_awaited()
        self.assertIn('"game_state"', b.send.await_args.args[0])

    def test_a_session_with_no_live_socket_is_a_no_op(self):
        a = self._socket(1)
        server = self._server_with(a)

        asyncio.run(server.send_to_session(99, {"type": "game_state"}))

        a.send.assert_not_awaited()

    def test_a_failed_send_does_not_raise_and_drops_the_socket(self):
        a = self._socket(1)
        a.send = AsyncMock(side_effect=RuntimeError("socket closed"))
        server = self._server_with(a)

        asyncio.run(server.send_to_session(1, {"type": "game_state"}))

        self.assertNotIn(a, server._clients.get("default", set()))


if __name__ == "__main__":
    unittest.main()
