# channel/api/handler.py
# Standalone WebSocket handler for channel subscription services.

from typing import Any, Dict, Optional

from bbsengine6.net import (
    ChannelState,
    channel_subscribe,
    channel_unsubscribe,
    channel_unsubscribe_all,
    channel_get_session_channels,
)


from bbsengine6.session import SessionManager


def _session_id_for(websocket: Any) -> int:
    """Return the stable session id for a websocket.

    Prefers ``_bbsengine6_session_id`` allocated by ``WebSocketServer``;
    falls back to ``id(websocket)`` for unit tests that pass mock
    websockets which don't allow attribute assignment.
    """
    return getattr(websocket, "_bbsengine6_session_id", id(websocket))


class BaseService:
    """Base class for message handlers."""

    def __init__(self, args: Any, session_manager: SessionManager):
        self.args = args
        self.sessions = session_manager

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        raise NotImplementedError


class ChannelServiceHandler(BaseService):
    """Handle channel subscription messages."""

    def __init__(
        self, args: Any, session_manager: SessionManager, channel_state: ChannelState
    ):
        super().__init__(args, session_manager)
        self.channel_state = channel_state

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        msg_type = message.get("type")
        session_id = _session_id_for(websocket)

        if msg_type == "subscribe_channel":
            return await self._handle_subscribe(session_id, message)
        elif msg_type == "unsubscribe_channel":
            return await self._handle_unsubscribe(session_id, message)
        elif msg_type == "get_subscriptions":
            return await self._handle_get_subscriptions(session_id)

        return None

    async def _handle_subscribe(
        self, session_id: int, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {
                "type": "error",
                "code": "invalid_request",
                "message": "channel required",
            }

        channel_subscribe(self.channel_state, session_id, channel)

        return {
            "type": "subscribed",
            "channel": channel,
            "message": f"Subscribed to {channel}",
        }

    async def _handle_unsubscribe(
        self, session_id: int, message: Dict[str, Any]
    ) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {
                "type": "error",
                "code": "invalid_request",
                "message": "channel required",
            }

        channel_unsubscribe(self.channel_state, session_id, channel)

        return {
            "type": "unsubscribed",
            "channel": channel,
            "message": f"Unsubscribed from {channel}",
        }

    async def _handle_get_subscriptions(self, session_id: int) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channels = channel_get_session_channels(self.channel_state, session_id)

        return {
            "type": "subscriptions",
            "channels": list(channels),
        }


class MessageRouter:
    """Main message handler for channel WebSocket services."""

    def __init__(
        self,
        args: Any,
        channel_state: Optional[ChannelState] = None,
        server: Any = None,
    ):
        self.args = args
        self.sessions = SessionManager()
        # Accept a shared state from the caller (typically BED) so that
        # server.publish(...) and ChannelServiceHandler see the same
        # subscriptions. Falls back to a private state for callers that
        # don't share (legacy behavior, but in that case publishes
        # through server.publish will not reach these subscribers).
        self.channel_state = (
            channel_state if channel_state is not None else ChannelState()
        )
        self.server = server
        self.channel_service = ChannelServiceHandler(
            args, self.sessions, self.channel_state
        )

    def register_all(self, server: Any) -> None:
        """Register all services with the WebSocketServer."""
        server.register_service(
            self.channel_service,
            [
                "subscribe_channel",
                "unsubscribe_channel",
                "get_subscriptions",
            ],
        )
        # Allow the server to call back on disconnect for cleanup.
        if self.server is None:
            self.server = server
        server.register_router(self)

    def unregister_session(self, session_id: int) -> None:
        """Clean up session on disconnect.

        Unsubscribes from all channels and removes the session record
        so the connection no longer holds any pub/sub state.
        """
        channel_unsubscribe_all(self.channel_state, session_id)
        self.sessions.unregister_session(session_id)
