"""Regression tests for net robustness fixes.

Covers:
  - channel_publish / broadcast iterate snapshots (no RuntimeError when a
    client is removed while a send is awaiting).
  - WebSocketServer refuses a connection it cannot stamp with a session id
    (no id(websocket) fallback).
  - recv_with_length enforces an optional max_len before allocating.
  - Packet decoders authenticate the trailing HMAC before parsing fields.
"""

import asyncio
import os
import socket
import struct
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from bbsengine6.net.crypto import CryptoHash, PacketAuthError  # noqa: E402
from bbsengine6.net.packet_codec import (  # noqa: E402
    decode_file_packet,
    decode_message_packet,
    encode_file_packet,
    encode_message_packet,
)
from bbsengine6.net.socket import recv_with_length, send_with_length  # noqa: E402
from bbsengine6.net.transport import (  # noqa: E402
    ChannelState,
    WebSocketServer,
    channel_publish,
)


class TestChannelPublishSnapshot(unittest.TestCase):
    def test_client_removed_during_send_does_not_raise(self):
        """A socket removed from _clients while awaiting send must not break
        iteration. Before the fix, iterating the live set raised
        RuntimeError: Set changed size during iteration."""

        async def run():
            server = WebSocketServer(host="127.0.0.1", port=0)
            state = ChannelState()

            ws_a = MagicMock(name="ws_a")
            ws_b = MagicMock(name="ws_b")
            ws_a._bbsengine6_session_id = 1
            ws_b._bbsengine6_session_id = 2

            clients = server._clients.setdefault("default", set())
            clients.update({ws_a, ws_b})

            state.channels["chan"] = {1, 2}

            async def send_and_drop(msg):
                # Simulate on_connect's finally removing a client mid-publish.
                clients.discard(ws_b)

            ws_a.send = AsyncMock(side_effect=send_and_drop)
            ws_b.send = AsyncMock()

            await channel_publish(state, "chan", {"t": "x"}, server)
            self.assertTrue(ws_a.send.await_count == 1)

        asyncio.run(run())


class TestSessionStampRefusal(unittest.TestCase):
    def test_on_connect_closes_when_session_stamp_fails(self):
        """Drive the real on_connect via the server's handler: a websocket that
        rejects attribute assignment must be closed and never registered in
        _clients, rather than being keyed on id(websocket)."""

        class NoAttrs:
            __slots__ = ("transport", "closed", "path")

            def __init__(self):
                self.transport = MagicMock()
                self.transport.get_extra_info.return_value = None
                self.closed = False
                self.path = "/default"

            def __aiter__(self):
                return self

            async def __anext__(self):
                raise StopAsyncIteration

            async def close(self):
                self.closed = True

        async def run():
            server = WebSocketServer(host="127.0.0.1", port=0)
            ws = NoAttrs()
            # Pull the on_connect closure out of start() by capturing the
            # handler passed to websockets.serve.
            captured = {}

            async def fake_serve(handler, **kwargs):
                captured["handler"] = handler
                return MagicMock()

            from unittest.mock import patch

            with patch("websockets.serve", side_effect=fake_serve), patch(
                "bbsengine6.net.transport.socket.getaddrinfo",
                return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
            ):
                await server.start()
            await captured["handler"](ws)
            return ws, server

        ws, server = asyncio.run(run())
        self.assertTrue(ws.closed)
        self.assertEqual(server.get_clients(), 0)


class TestRecvWithLengthBound(unittest.TestCase):
    def test_default_unbounded_roundtrip_unchanged(self):
        a, b = socket.socketpair()
        try:
            send_with_length(a, b"hello")
            self.assertEqual(recv_with_length(b), b"hello")
        finally:
            a.close()
            b.close()

    def test_rejects_declared_length_over_max(self):
        a, b = socket.socketpair()
        try:
            a.sendall(struct.pack("!I", 1_000_000))
            with self.assertRaises(ValueError):
                recv_with_length(b, max_len=1024)
        finally:
            a.close()
            b.close()

    def test_accepts_length_within_max(self):
        a, b = socket.socketpair()
        try:
            send_with_length(a, b"x" * 100)
            self.assertEqual(recv_with_length(b, max_len=1024), b"x" * 100)
        finally:
            a.close()
            b.close()


class TestTrailingHmacFirst(unittest.TestCase):
    def setUp(self):
        self.crypto = CryptoHash(b"k" * 32)

    def test_file_packet_with_bad_mac_rejected_before_parse(self):
        blob = encode_file_packet(_file_packet(), crypto=self.crypto)
        tampered = blob[:-1] + (b"0" if blob[-1:] != b"0" else b"1")
        with self.assertRaises(PacketAuthError):
            decode_file_packet(tampered, crypto=self.crypto)

    def test_message_packet_with_bad_mac_rejected(self):
        blob = encode_message_packet(_message_packet(), crypto=self.crypto)
        tampered = blob[:-1] + (b"0" if blob[-1:] != b"0" else b"1")
        with self.assertRaises(PacketAuthError):
            decode_message_packet(tampered, crypto=self.crypto)

    def test_truncated_packet_with_crypto_raises_auth_error(self):
        with self.assertRaises(PacketAuthError):
            decode_file_packet(b"\x00" * 10, crypto=self.crypto)


def _file_packet():
    from bbsengine6.net.packet import BlockPacket  # noqa: F401

    from bbsengine6.net.packet_types import FilePacket  # type: ignore

    return FilePacket(
        packet_id=1,
        filename="a.txt",
        mime_type="text/plain",
        file_size=3,
        total_blocks=1,
        block_id=0,
        blocks=[b"abc"],
    )


def _message_packet():
    from bbsengine6.net.packet_types import MessagePacket  # type: ignore

    return MessagePacket(
        packet_id=1,
        sender="alice",
        subject="hi",
        content_type="text/plain",
        content=b"body",
    )


if __name__ == "__main__":
    unittest.main()
