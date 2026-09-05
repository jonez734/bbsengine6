# bbsengine6/net/defaultrouter.py
# DefaultRouter - Minimal stub router for BED
# Handles only auth/ping as example

from typing import Any, Dict, Optional


class DefaultRouter:
    """Minimal stub router - handles only auth/ping as example."""

    def __init__(
        self,
        args: Any,
        *,
        channel_state: Optional["ChannelState"] = None,
        server: Any = None,
        **kwargs,
    ):
        # Accept (and ignore) auth-wiring kwargs forwarded by bed.main.BED.start
        # so DefaultRouter stays compatible with routers that do consume them.
        # See bed.main for the kwarg contract.
        self.args = args
        self.sessions: Dict[int, Dict[str, Any]] = {}
        self.channel_state = channel_state
        self.server = server
        self._channel_router: Any = None

    def register_all(self, server: Any) -> None:
        """Register message handlers with the WebSocket server.

        The `list_services` message type is answered directly by
        `WebSocketServer.dispatch_message`; routers do not register
        their own copy.

        Also wires the channel subscription handler
        (``subscribe_channel`` / ``unsubscribe_channel`` / ``get_subscriptions``)
        via bbsengine6.channel.api.handler.MessageRouter so even a minimal
        deployment exposes pub/sub without each app having to wire it
        manually. The channel handler is a no-op when ``enabled: false``
        in the channel config.
        """
        server.register_service(self, ["auth", "ping"])

        # Lazily import to avoid pulling the channel package into callers
        # that don't reach this path (e.g. unit tests that never invoke
        # register_all). The import is cheap and idempotent at runtime.
        from bbsengine6.channel.api.handler import MessageRouter as ChannelRouter

        self._channel_router = ChannelRouter(
            self.args,
            channel_state=self.channel_state,
            server=server,
        )
        self._channel_router.register_all(server)
        if self.server is None:
            self.server = server

    async def handle_message(
        self, server: Any, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle incoming message."""
        msg_type = message.get("type")

        if msg_type == "auth":
            return await self._handle_auth(websocket, message)
        elif msg_type == "ping":
            return await self._handle_ping()

        return None

    async def _handle_auth(self, websocket: Any, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle auth message."""
        moniker = message.get("moniker", "")
        password = message.get("password", "")

        session_id = id(websocket)
        self.sessions[session_id] = {"moniker": moniker}

        return {
            "type": "auth_result",
            "success": True,
            "moniker": moniker,
            "balance": 0,
            "message": "Authenticated (stub)",
        }

    async def _handle_ping(self) -> Dict[str, Any]:
        """Handle ping message."""
        return {"type": "pong"}
