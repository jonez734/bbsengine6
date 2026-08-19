# test_message_channel.py
# Tests for the message system channel subscription functionality (Phase 1A)

from typing import Any, Optional

from bbsengine6.net.transport import (
    ChannelState,
    channel_subscribe,
    channel_unsubscribe,
    channel_unsubscribe_all,
    channel_register_callback,
    channel_unregister_callback,
    channel_unregister_all_callbacks,
    channel_get_subscribers,
    channel_get_session_channels,
    channel_publish,
)


class TestChannelSubscribe:
    """Tests for channel subscription."""

    def test_subscribe_to_channel(self):
        """Session subscribes to channel."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")

        assert 1 in channel_get_subscribers(state, "casino:table:blackjack-1")
        assert "casino:table:blackjack-1" in channel_get_session_channels(state, 1)

    def test_subscribe_multiple_sessions(self):
        """Multiple sessions can subscribe to same channel."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_subscribe(state, session_id=2, channel="casino:table:blackjack-1")

        subscribers = channel_get_subscribers(state, "casino:table:blackjack-1")
        assert subscribers == {1, 2}

    def test_subscribe_multiple_channels(self):
        """Session can subscribe to multiple channels."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_subscribe(state, session_id=1, channel="system:shout")

        assert "casino:table:blackjack-1" in channel_get_session_channels(state, 1)
        assert "system:shout" in channel_get_session_channels(state, 1)


class TestChannelUnsubscribe:
    """Tests for channel unsubscription."""

    def test_unsubscribe_from_channel(self):
        """Session unsubscribes from channel."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_unsubscribe(state, session_id=1, channel="casino:table:blackjack-1")

        assert 1 not in channel_get_subscribers(state, "casino:table:blackjack-1")
        assert "casino:table:blackjack-1" not in channel_get_session_channels(state, 1)

    def test_unsubscribe_all_on_disconnect(self):
        """Cleanup on session disconnect."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_subscribe(state, session_id=1, channel="member:alice")
        channel_unsubscribe_all(state, session_id=1)

        assert 1 not in channel_get_subscribers(state, "casino:table:blackjack-1")
        assert 1 not in channel_get_subscribers(state, "member:alice")
        assert "casino:table:blackjack-1" not in channel_get_session_channels(state, 1)

    def test_unsubscribe_preserves_other_sessions(self):
        """Unsubscribing one session preserves others."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_subscribe(state, session_id=2, channel="casino:table:blackjack-1")
        channel_unsubscribe(state, session_id=1, channel="casino:table:blackjack-1")

        subscribers = channel_get_subscribers(state, "casino:table:blackjack-1")
        assert subscribers == {2}


class TestChannelPublish:
    """Tests for message publishing."""

    def test_publish_to_channel(self):
        """Message published to channel reaches subscribers."""
        state = ChannelState()
        received_messages = []

        def callback(msg):
            received_messages.append(msg)

        channel_subscribe(state, session_id=1, channel="casino:table:blackjack-1")
        channel_register_callback(state, "casino:table:blackjack-1", callback)

        import asyncio

        async def run():
            await channel_publish(
                state,
                channel="casino:table:blackjack-1",
                message={"type": "game_state", "hand": "player_cards"},
                server=None,
            )

        asyncio.run(run())

        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "game_state"

    def test_publish_empty_channel(self):
        """Publishing to channel with no subscribers doesn't error."""
        import asyncio

        state = ChannelState()

        async def run():
            # Should not raise
            await channel_publish(
                state,
                channel="casino:table:empty",
                message={"type": "test"},
                server=None,
            )

        asyncio.run(run())
        # If we get here without error, test passes


class TestCallbackRegistration:
    """Tests for bot callback registration."""

    def test_register_callback(self):
        """Bot registers callback for channel."""
        state = ChannelState()

        def my_callback(msg):
            pass

        channel_register_callback(state, "casino:table:blackjack-1", my_callback)

        assert my_callback in state.callbacks["casino:table:blackjack-1"]

    def test_callback_invoked_on_publish(self):
        """Callback receives published messages."""
        state = ChannelState()
        received = []

        def callback(msg):
            received.append(msg)

        channel_register_callback(state, "member:alice", callback)

        import asyncio

        async def run():
            await channel_publish(
                state,
                channel="member:alice",
                message={"type": "direct_message", "from": "bob", "content": "hi"},
                server=None,
            )

        asyncio.run(run())

        assert len(received) == 1
        assert received[0]["from"] == "bob"

    def test_multiple_callbacks_per_channel(self):
        """Multiple bots can register on same channel."""
        state = ChannelState()
        received1 = []
        received2 = []

        def callback1(msg):
            received1.append(msg)

        def callback2(msg):
            received2.append(msg)

        channel_register_callback(state, "casino:table:blackjack-1", callback1)
        channel_register_callback(state, "casino:table:blackjack-1", callback2)

        import asyncio

        async def run():
            await channel_publish(
                state,
                channel="casino:table:blackjack-1",
                message={"type": "game_state"},
                server=None,
            )

        asyncio.run(run())

        assert len(received1) == 1
        assert len(received2) == 1


class TestMemberChannel:
    """Tests for member:moniker direct messaging."""

    def test_member_channel_subscribe(self):
        """Subscribe to own member:moniker channel."""
        state = ChannelState()
        channel_subscribe(state, session_id=1, channel="member:alice")

        assert "member:alice" in channel_get_session_channels(state, 1)

    def test_direct_message_via_member_channel(self):
        """Direct message via member:channel delivers to that member."""
        state = ChannelState()
        received = []

        def callback(msg):
            received.append(msg)

        channel_subscribe(state, session_id=1, channel="member:alice")
        channel_register_callback(state, "member:alice", callback)

        import asyncio

        async def run():
            await channel_publish(
                state,
                channel="member:alice",
                message={"type": "chat", "from": "bob", "content": "hello alice"},
                server=None,
            )

        asyncio.run(run())

        assert len(received) == 1
        assert received[0]["content"] == "hello alice"


class TestSharedChannelState:
    """Regression: WebSocketServer must use the same ChannelState as
    subscribers so server.publish(...) reaches them.

    Pre-fix: WebSocketServer constructed its own ChannelState
    internally; the ChannelServiceHandler had a separate one. As a
    result, server.publish(...) saw zero subscribers.
    """

    def test_server_uses_passed_state(self):
        """A state passed to the server is the one publish() uses."""
        from bbsengine6.net.transport import WebSocketServer

        state = ChannelState()
        server = WebSocketServer(host="127.0.0.1", port=18765, channel_state=state)
        assert server._channel_state is state

    def test_server_creates_state_when_none_passed(self):
        """Default behavior (no shared state) creates an internal one."""
        from bbsengine6.net.transport import WebSocketServer

        server = WebSocketServer(host="127.0.0.1", port=18766)
        assert server._channel_state is not None
        assert isinstance(server._channel_state, ChannelState)

    def test_publish_uses_shared_state(self):
        """Publish reaches subscribers registered against the shared state."""
        from bbsengine6.net.transport import WebSocketServer

        async def run():
            state = ChannelState()
            server = WebSocketServer(host="127.0.0.1", port=18767, channel_state=state)
            # Subscriber registers against the shared state directly.
            channel_subscribe(state, session_id=42, channel="test:chan")
            received = []

            def cb(msg):
                received.append(msg)

            channel_register_callback(state, "test:chan", cb)
            await server.publish("test:chan", {"hello": "world"})
            return received

        import asyncio

        result = asyncio.run(run())
        assert result == [{"hello": "world"}]


class TestCallbackLifecycle:
    """Callback registration must be idempotent and reversible."""

    def test_register_same_callback_twice_dedupes(self):
        """Re-registering the same callable does not double-invoke."""
        state = ChannelState()
        received = []

        def cb(msg):
            received.append(msg)

        channel_register_callback(state, "c", cb)
        channel_register_callback(state, "c", cb)
        channel_register_callback(state, "c", cb)

        import asyncio

        asyncio.run(channel_publish(state, channel="c", message={"x": 1}))
        assert len(received) == 1

    def test_unregister_callback_removes(self):
        """After unregister, callback is not invoked."""
        state = ChannelState()
        received = []

        def cb(msg):
            received.append(msg)

        channel_register_callback(state, "c", cb)
        removed = channel_unregister_callback(state, "c", cb)
        assert removed is True

        import asyncio

        asyncio.run(channel_publish(state, channel="c", message={"x": 1}))
        assert received == []

    def test_unregister_unknown_callback_returns_false(self):
        state = ChannelState()
        removed = channel_unregister_callback(state, "c", lambda m: None)
        assert removed is False

    def test_unregister_unknown_channel_returns_false(self):
        state = ChannelState()
        removed = channel_unregister_callback(state, "missing", lambda m: None)
        assert removed is False

    def test_unregister_all_callbacks_for_channel(self):
        state = ChannelState()
        channel_register_callback(state, "c1", lambda m: None)
        channel_register_callback(state, "c1", lambda m: None)
        channel_register_callback(state, "c2", lambda m: None)

        n = channel_unregister_all_callbacks(state, "c1")
        assert n == 2
        assert "c1" not in state.callbacks
        assert "c2" in state.callbacks

    def test_unregister_all_callbacks_all_channels(self):
        state = ChannelState()
        channel_register_callback(state, "c1", lambda m: None)
        channel_register_callback(state, "c2", lambda m: None)
        channel_register_callback(state, "c2", lambda m: None)

        n = channel_unregister_all_callbacks(state)
        assert n == 3
        assert state.callbacks == {}


class TestSessionIdAllocation:
    """The server must allocate a monotonic session id per connection."""

    def test_alloc_session_id_is_monotonic(self):
        from bbsengine6.net.transport import WebSocketServer

        server = WebSocketServer(host="127.0.0.1", port=18768)
        ids = [server._alloc_session_id() for _ in range(5)]
        assert ids == sorted(ids)
        assert len(set(ids)) == 5
        assert all(i > 0 for i in ids)

    def test_session_id_does_not_collide_after_release(self):
        """Even after a high id, the next allocation continues monotonically."""
        from bbsengine6.net.transport import WebSocketServer

        server = WebSocketServer(host="127.0.0.1", port=18769)
        a = server._alloc_session_id()
        b = server._alloc_session_id()
        assert a != b
        c = server._alloc_session_id()
        assert c > b

    def test_session_manager_allocates_ids(self):
        """SessionManager.alloc_session_id returns monotonic ids."""
        from bbsengine6.session import SessionManager

        sm = SessionManager()
        ids = [sm.alloc_session_id() for _ in range(3)]
        assert ids == sorted(ids)
        assert len(set(ids)) == 3
        assert all(i > 0 for i in ids)

    def test_server_uses_provided_session_manager(self):
        """A SessionManager passed to the server is reused for ids."""
        from bbsengine6.net.transport import WebSocketServer
        from bbsengine6.session import SessionManager

        sm = SessionManager()
        server = WebSocketServer(host="127.0.0.1", port=18770, session_manager=sm)
        assert server._sessions is sm
        sid = server._alloc_session_id()
        assert sm.get_moniker(sid) is None  # not registered yet


class _MockWebSocket:
    """Lightweight websocket stand-in for channel_publish unit tests.

    Records every ``send`` payload so tests can assert on delivery. The
    server only needs ``_bbsengine6_session_id`` (for transport-allocated
    ids) and ``id(ws)`` (the Python object id fallback) to identify a
    subscriber; ``send`` is the only method it ever calls.
    """

    def __init__(self, bbs_session_id: int) -> None:
        self._bbsengine6_session_id = bbs_session_id
        self.sent: list = []
        self.send_error: Optional[Exception] = None

    async def send(self, payload) -> None:
        if self.send_error is not None:
            raise self.send_error
        self.sent.append(payload)


class TestChannelPublishWebSocketFanOut:
    """Regression tests for the WS fan-out path of ``channel_publish``.

    The previous implementation routed via
    ``server.broadcast(message, path=f"channel:{channel}")``, which only
    reaches clients connected to that exact path. Casino clients connect
    to path ``default``, so the broadcast was silently dropped. These
    tests pin the corrected behaviour: subscribers identified by either
    ``id(ws)`` or ``ws._bbsengine6_session_id`` get a JSON payload sent
    over their websocket, non-subscribers don't, and the dedupe guard
    prevents double-delivery when a single ws is subscribed under both
    keys.
    """

    def _make_server(self) -> Any:
        from bbsengine6.net.transport import WebSocketServer

        return WebSocketServer(host="127.0.0.1", port=0)

    def test_subscriber_via_bbsengine6_session_id_receives_publish(self):
        """Subscriber keyed by transport-allocated id gets the message."""
        import json
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws = _MockWebSocket(bbs_session_id=42)
            server._clients["default"] = {ws}
            channel_subscribe(state, 42, "casino:table:test")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state", "phase": "waiting"},
                server=server,
            )

            assert len(ws.sent) == 1, f"expected 1 send, got {ws.sent}"
            payload = json.loads(ws.sent[0])
            assert payload == {"type": "game_state", "phase": "waiting"}

        asyncio.run(run())

    def test_subscriber_via_python_id_fallback_receives_publish(self):
        """Subscriber keyed by id(ws) (legacy path) gets the message."""
        import json
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws = _MockWebSocket(bbs_session_id=99)
            server._clients["default"] = {ws}
            # Subscribe using the Python id() fallback, the way casino's
            # _legacy_session_id used to work before normalization.
            channel_subscribe(state, id(ws), "casino:table:test")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state", "phase": "dealing"},
                server=server,
            )

            assert len(ws.sent) == 1, f"expected 1 send, got {ws.sent}"
            payload = json.loads(ws.sent[0])
            assert payload == {"type": "game_state", "phase": "dealing"}

        asyncio.run(run())

    def test_non_subscriber_does_not_receive_publish(self):
        """A websocket on the server but not subscribed to the channel
        must not be sent the message."""
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws_subscribed = _MockWebSocket(bbs_session_id=1)
            ws_unrelated = _MockWebSocket(bbs_session_id=2)
            ws_other_channel = _MockWebSocket(bbs_session_id=3)
            server._clients["default"] = {ws_subscribed, ws_unrelated, ws_other_channel}
            channel_subscribe(state, 1, "casino:table:test")
            channel_subscribe(state, 3, "casino:table:other")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state"},
                server=server,
            )

            assert len(ws_subscribed.sent) == 1
            assert ws_unrelated.sent == []
            assert ws_other_channel.sent == []

        asyncio.run(run())

    def test_publish_without_server_skips_ws_fanout_but_still_invokes_callbacks(self):
        """``server=None`` skips WS delivery but registered callbacks
        still fire (in-process bots must keep working)."""
        import asyncio

        async def run():
            state = ChannelState()

            received = []
            channel_register_callback(state, "casino:table:test", received.append)
            channel_subscribe(state, 42, "casino:table:test")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state"},
                server=None,
            )

            assert received == [{"type": "game_state"}]

        asyncio.run(run())

    def test_publish_does_not_double_deliver_when_subscribed_under_both_ids(self):
        """If the same ws is subscribed under both id-spaces, it must
        receive exactly one message, not two."""
        import json
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws = _MockWebSocket(bbs_session_id=10)
            server._clients["default"] = {ws}
            channel_subscribe(state, 10, "casino:table:test")
            channel_subscribe(state, id(ws), "casino:table:test")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state"},
                server=server,
            )

            assert len(ws.sent) == 1, f"expected exactly 1 send, got {ws.sent}"
            payload = json.loads(ws.sent[0])
            assert payload == {"type": "game_state"}

        asyncio.run(run())

    def test_publish_to_channel_with_no_subscribers_is_noop(self):
        """Publishing to a channel nobody is subscribed to must not
        attempt any send and must not raise."""
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws = _MockWebSocket(bbs_session_id=1)
            server._clients["default"] = {ws}
            channel_subscribe(state, 1, "casino:table:other")

            await channel_publish(
                state,
                "casino:table:empty",
                {"type": "game_state"},
                server=server,
            )

            assert ws.sent == []

        asyncio.run(run())

    def test_publish_swallows_send_errors_and_continues(self):
        """A failing send on one subscriber must not prevent delivery to
        other subscribers."""
        import json
        import asyncio

        async def run():
            state = ChannelState()
            server = self._make_server()

            ws_bad = _MockWebSocket(bbs_session_id=1)
            ws_bad.send_error = RuntimeError("socket closed")
            ws_good = _MockWebSocket(bbs_session_id=2)
            server._clients["default"] = {ws_bad, ws_good}
            channel_subscribe(state, 1, "casino:table:test")
            channel_subscribe(state, 2, "casino:table:test")

            await channel_publish(
                state,
                "casino:table:test",
                {"type": "game_state"},
                server=server,
            )

            assert ws_bad.sent == []
            assert len(ws_good.sent) == 1
            assert json.loads(ws_good.sent[0]) == {"type": "game_state"}

        asyncio.run(run())
