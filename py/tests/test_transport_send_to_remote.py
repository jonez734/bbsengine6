# test_transport_send_to_remote.py
# Tests for WebSocketTransport.send_to_remote() real-network impl.

import asyncio
import json
from typing import Any, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch


from bbsengine6.net.transport import WebSocketTransport


class _FakeWebSocket:
    """Minimal async-context-manager stand-in for a websockets.WebSocketClientProtocol."""

    def __init__(self, ack: Optional[str] = None) -> None:
        self.sent: List[str] = []
        self.ack = ack
        self._closed = False

    async def __aenter__(self) -> "_FakeWebSocket":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        self._closed = True

    async def send(self, payload: str) -> None:
        self.sent.append(payload)

    async def recv(self) -> str:
        if self.ack is None:
            # Block forever so wait_for hits its timeout.
            await asyncio.sleep(60)
        return self.ack


def _connect_mock(fake: _FakeWebSocket) -> MagicMock:
    """Build a mock for ``websockets.connect(url)`` that returns ``fake``
    when used as an async context manager.
    """
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=fake)
    cm.__aexit__ = AsyncMock(return_value=None)
    fn = MagicMock(return_value=cm)
    return fn


class TestSendToRemote:
    """send_to_remote must open a real WebSocket and send the payload."""

    def test_sends_payload_to_expected_url(self) -> None:
        transport = WebSocketTransport(timeout=5.0)
        fake = _FakeWebSocket(ack=None)
        mock_connect = _connect_mock(fake)

        async def run() -> Tuple[bool, str]:
            with patch("websockets.connect", new=mock_connect):
                result = await transport.send_to_remote(
                    machine_host="example.com",
                    machine_port=8765,
                    recipients=["alice", "bob"],
                    message_data={"content": "hi"},
                )
                mock_connect.assert_called_once()
                url_arg = mock_connect.call_args[0][0]
                assert url_arg == "ws://example.com:8765/message"
                return result

        ok, msg = asyncio.run(run())
        assert ok is True
        assert "2 recipients" in msg
        assert len(fake.sent) == 1
        sent = json.loads(fake.sent[0])
        assert sent["type"] == "message"
        assert sent["recipients"] == ["alice", "bob"]
        assert sent["data"] == {"content": "hi"}

    def test_includes_auth_token_when_provided(self) -> None:
        transport = WebSocketTransport(timeout=5.0)
        fake = _FakeWebSocket(ack=None)

        async def run() -> None:
            with patch("websockets.connect", new=_connect_mock(fake)):
                await transport.send_to_remote(
                    "example.com",
                    8765,
                    ["alice"],
                    {"content": "hi"},
                    auth_token="secret-token",
                )

        asyncio.run(run())
        sent = json.loads(fake.sent[0])
        assert sent["auth_token"] == "secret-token"

    def test_returns_false_on_connection_refused(self) -> None:
        transport = WebSocketTransport(timeout=5.0)

        async def run() -> Tuple[bool, str]:
            with patch(
                "websockets.connect",
                new=MagicMock(side_effect=ConnectionRefusedError("nope")),
            ):
                return await transport.send_to_remote(
                    "example.com", 8765, ["alice"], {"content": "hi"}
                )

        ok, msg = asyncio.run(run())
        assert ok is False
        assert "connection error" in msg.lower() or "websocket" in msg.lower()

    def test_returns_false_on_websocket_exception(self) -> None:
        import websockets.exceptions

        transport = WebSocketTransport(timeout=5.0)

        async def run() -> Tuple[bool, str]:
            with patch(
                "websockets.connect",
                new=MagicMock(
                    side_effect=websockets.exceptions.WebSocketException("boom")
                ),
            ):
                return await transport.send_to_remote(
                    "example.com", 8765, ["alice"], {"content": "hi"}
                )

        ok, msg = asyncio.run(run())
        assert ok is False
        assert "websocket" in msg.lower()

    def test_returns_false_on_timeout(self) -> None:
        """A hanging connection that exceeds self.timeout is reported."""
        transport = WebSocketTransport(timeout=0.05)
        fake = _FakeWebSocket(ack=None)

        # The actual websockets.connect call is fast (returns a fake);
        # the recv() inside the context manager is what hangs. The
        # outer asyncio.timeout will fire because recv() never
        # completes within self.timeout.
        async def run() -> Tuple[bool, str]:
            with patch("websockets.connect", new=_connect_mock(fake)):
                return await transport.send_to_remote(
                    "example.com", 8765, ["alice"], {"content": "hi"}
                )

        ok, msg = asyncio.run(run())
        assert ok is False
        assert "timeout" in msg.lower()

    def test_ack_frame_does_not_block_send(self) -> None:
        """Server sends an ack; we still return success promptly."""
        transport = WebSocketTransport(timeout=5.0)
        fake = _FakeWebSocket(ack="OK")

        async def run() -> Tuple[bool, str]:
            with patch("websockets.connect", new=_connect_mock(fake)):
                return await transport.send_to_remote(
                    "example.com", 8765, ["alice"], {"content": "hi"}
                )

        ok, msg = asyncio.run(run())
        assert ok is True
        assert "1 recipients" in msg

    def test_no_ack_within_window_does_not_fail(self) -> None:
        """Server doesn't ack; we still return success after timeout."""
        transport = WebSocketTransport(timeout=5.0)

        class _NoAckFake(_FakeWebSocket):
            def __init__(self) -> None:
                super().__init__(ack=None)

            async def recv(self) -> str:
                await asyncio.sleep(0.01)
                raise asyncio.TimeoutError()

        fake = _NoAckFake()

        async def run() -> Tuple[bool, str]:
            with patch("websockets.connect", new=_connect_mock(fake)):
                return await transport.send_to_remote(
                    "example.com", 8765, ["alice"], {"content": "hi"}
                )

        ok, msg = asyncio.run(run())
        assert ok is True
        assert len(fake.sent) == 1
