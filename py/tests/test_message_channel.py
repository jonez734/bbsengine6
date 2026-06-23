# test_message_channel.py
# Tests for the message system channel subscription functionality (Phase 1A)

import pytest
from bbsengine6.net.transport import (
    ChannelState,
    channel_subscribe,
    channel_unsubscribe,
    channel_unsubscribe_all,
    channel_register_callback,
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


# =============================================================================
# Phase 1B: Persistence Tests
# These tests require database tables that will be created in Phase 1B
# =============================================================================

pytest.mark.skip(reason="Phase 1B: Requires engine.__message table")


class TestMessagePersistence:
    """Tests for message persistence (Phase 1B)."""

    def test_message_persistence(self):
        """Messages stored in DB, delivered to offline users."""
        pytest.skip("Requires engine.__message table")

    def test_message_delivery_tracking(self):
        """Automatic delivery tracking on connect."""
        pytest.skip("Requires engine.__message_recipient table")

    def test_message_read_receipt(self):
        """Client acknowledges receipt."""
        pytest.skip("Requires engine.__message table")


# =============================================================================
# Phase 1C: Groups, Blocking, Rate Limiting Tests
# These tests require database tables that will be created in Phase 1C
# =============================================================================

pytest.mark.skip(reason="Phase 1C: Requires message group/block tables")


class TestMessageGroups:
    """Tests for message groups (Phase 1C)."""

    def test_message_groups(self):
        """@everyone and custom groups."""
        pytest.skip("Requires engine.__message_group table")

    def test_message_rate_limiting(self):
        """Per-sender, per-channel rate limits."""
        pytest.skip("Requires engine.__message_rate_limit table")

    def test_message_blocking(self):
        """Sender blocked by recipient."""
        pytest.skip("Requires engine.__message_block table")

    def test_message_urgency(self):
        """Priority levels (ROUTINE, IMPORTANT, URGENT, CRITICAL)."""
        pytest.skip("Requires urgency column in engine.__message table")


# =============================================================================
# Phase 1D: Multi-Channel Delivery Tests
# =============================================================================

pytest.mark.skip(reason="Phase 1D: Requires delivery handlers")


class TestMessageMultiChannel:
    """Tests for multi-channel delivery (Phase 1D)."""

    def test_message_multi_channel(self):
        """Email, SMS delivery via subscribed handlers."""
        pytest.skip("Requires delivery handler implementation")


# =============================================================================
# Phase 1E: Templating Tests
# =============================================================================

pytest.mark.skip(reason="Phase 1E: Requires templating implementation")


class TestMessageTemplating:
    """Tests for message templating (Phase 1E)."""

    def test_message_templating(self):
        """Variable substitution in messages."""
        pytest.skip("Requires template rendering in message system")
