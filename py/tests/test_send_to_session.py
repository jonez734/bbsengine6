"""WebSocketServer.send_to_session sends a message to the one live socket bound to a connection.

Bed keys sessions by the connection's websocket id, which the websockets library makes a UUID, so the transport
routes by that same key. A session with no live socket is a no-op, not an error.
"""

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, MagicMock

from bbsengine6.net.transport import WebSocketServer


class TestSendToSession(unittest.TestCase):
    def _server_with(self, *sockets):
        server = WebSocketServer(host="127.0.0.1", port=0)
        clients = server._clients.setdefault("default", set())
        clients.update(sockets)
        return server

    def _socket(self, connection_id):
        ws = MagicMock(name=f"ws_{connection_id}")
        ws.id = connection_id  # the websockets library's per-connection UUID
        ws.send = AsyncMock()
        return ws

    def test_sends_only_to_the_socket_of_the_connection(self):
        a_id, b_id = uuid.uuid4(), uuid.uuid4()
        a, b = self._socket(a_id), self._socket(b_id)
        server = self._server_with(a, b)

        asyncio.run(server.send_to_session(str(b_id), {"type": "game_state", "phase": "playing"}))

        b.send.assert_awaited_once()
        a.send.assert_not_awaited()
        self.assertIn('"game_state"', b.send.await_args.args[0])

    def test_a_connection_with_no_live_socket_is_a_no_op(self):
        a = self._socket(uuid.uuid4())
        server = self._server_with(a)

        asyncio.run(server.send_to_session(str(uuid.uuid4()), {"type": "game_state"}))

        a.send.assert_not_awaited()

    def test_a_failed_send_does_not_raise_and_drops_the_socket(self):
        cid = uuid.uuid4()
        a = self._socket(cid)
        a.send = AsyncMock(side_effect=RuntimeError("socket closed"))
        server = self._server_with(a)

        asyncio.run(server.send_to_session(str(cid), {"type": "game_state"}))

        self.assertNotIn(a, server._clients.get("default", set()))


if __name__ == "__main__":
    unittest.main()
