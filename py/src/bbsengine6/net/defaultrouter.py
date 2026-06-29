# bbsengine6/net/defaultrouter.py
# DefaultRouter - Minimal stub router for BED
# Handles only auth/ping as example

from typing import Any, Dict, Optional


class DefaultRouter:
    """Minimal stub router - handles only auth/ping as example."""

    def __init__(self, args: Any):
        self.args = args
        self.sessions: Dict[int, Dict[str, Any]] = {}

    def register_all(self, server: Any) -> None:
        """Register message handlers with the WebSocket server.

        The `list_services` message type is answered directly by
        `WebSocketServer.dispatch_message`; routers do not register
        their own copy.
        """
        server.register_service(self, ["auth", "ping"])

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
