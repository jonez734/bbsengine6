# channel/api/handler.py
# Standalone WebSocket handler for channel subscription services.

from typing import Any, Dict, Optional

from bbsengine6.net import (
    ChannelState,
    channel_subscribe,
    channel_unsubscribe,
    channel_get_session_channels,
)


class SessionManager:
    """Manages WebSocket sessions and authentication state."""

    def __init__(self):
        self._sessions: Dict[int, Dict[str, Any]] = {}

    def register_session(self, session_id: int, moniker: str, is_sysop: bool = False) -> None:
        self._sessions[session_id] = {"moniker": moniker, "is_sysop": is_sysop}

    def unregister_session(self, session_id: int) -> None:
        self._sessions.pop(session_id, None)

    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        return self._sessions.get(session_id)

    def get_moniker(self, session_id: int) -> Optional[str]:
        session = self._sessions.get(session_id)
        return session.get("moniker") if session else None


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

    def __init__(self, args: Any, session_manager: SessionManager, channel_state: ChannelState):
        super().__init__(args, session_manager)
        self.channel_state = channel_state

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        msg_type = message.get("type")

        if msg_type == "subscribe_channel":
            return await self._handle_subscribe(id(websocket), message)
        elif msg_type == "unsubscribe_channel":
            return await self._handle_unsubscribe(id(websocket), message)
        elif msg_type == "get_subscriptions":
            return await self._handle_get_subscriptions(id(websocket))

        return None

    async def _handle_subscribe(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {"type": "error", "code": "invalid_request", "message": "channel required"}

        channel_subscribe(self.channel_state, session_id, channel)

        return {
            "type": "subscribed",
            "channel": channel,
            "message": f"Subscribed to {channel}",
        }

    async def _handle_unsubscribe(self, session_id: int, message: Dict[str, Any]) -> Dict[str, Any]:
        moniker = self.sessions.get_moniker(session_id)
        if not moniker:
            return {"type": "error", "code": "not_authenticated"}

        channel = message.get("channel", "").strip()
        if not channel:
            return {"type": "error", "code": "invalid_request", "message": "channel required"}

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

    def __init__(self, args: Any):
        self.args = args
        self.sessions = SessionManager()
        self.channel_state = ChannelState()
        self.channel_service = ChannelServiceHandler(args, self.sessions, self.channel_state)

    def register_all(self, server: Any) -> None:
        """Register all services with the WebSocketServer."""
        server.register_service(self.channel_service, [
            "subscribe_channel", "unsubscribe_channel", "get_subscriptions",
        ])

    def unregister_session(self, session_id: int) -> None:
        """Clean up session on disconnect."""
        self.sessions.unregister_session(session_id)
