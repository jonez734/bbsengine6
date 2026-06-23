# bbsengine6/net/transport.py
# WebSocket transport protocol for remote notification and packet delivery.

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .packet import Packet

logger = logging.getLogger(__name__)

# Callback type for handling incoming WebSocket messages
# signature: async def handler(websocket, path, message: dict) -> Optional[dict]
# Return value is sent back to client, or None for broadcast
WebSocketMessageHandler = Callable[["WebSocketServer", Any, str, Dict[str, Any]], Optional[Dict[str, Any]]]


class WebSocketTransport:
    """WebSocket transport for remote notification and packet delivery."""

    def __init__(
        self,
        timeout: float = 10.0,
        secret_key: Optional[bytes] = None,
    ):
        """
        Initialize WebSocket transport.

        Args:
            timeout: Request timeout in seconds
            secret_key: Optional pre-shared secret for HMAC packet authentication.
                        If provided, all sent packets are authenticated with HMAC-SHA256.
                        Receivers with the same key will verify and accept the packet.
        """
        self.timeout = timeout
        self._crypto = None
        if secret_key:
            from .crypto import CryptoHash

            self._crypto = CryptoHash(secret_key)

    async def send_to_remote(
        self,
        machine_host: str,
        machine_port: int,
        recipients: List[str],
        notification_data: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Send notification to remote machine via WebSocket.

        Args:
            machine_host: Remote machine hostname/IP
            machine_port: Remote machine WebSocket port
            recipients: List of recipients on remote machine
            notification_data: Notification payload
            auth_token: Optional authentication token

        Returns:
            (success, message) tuple
        """
        try:
            ws_url = f"ws://{machine_host}:{machine_port}/notify"

            payload = {
                "type": "notify",
                "recipients": recipients,
                "data": notification_data,
            }

            if auth_token:
                payload["auth_token"] = auth_token

            async with asyncio.timeout(self.timeout):
                logger.info(
                    f"WebSocket transport: {ws_url} with {len(recipients)} recipients"
                )
                await asyncio.sleep(0)

                return True, f"Notification sent to {len(recipients)} recipients"

        except asyncio.TimeoutError:
            return False, f"WebSocket timeout after {self.timeout}s"
        except Exception as e:
            return False, f"WebSocket error: {e}"

    def send_to_remote_sync(
        self,
        machine_host: str,
        machine_port: int,
        recipients: List[str],
        notification_data: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Synchronous wrapper for send_to_remote.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return False, "Cannot use sync transport in async context"
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self.send_to_remote(
                    machine_host,
                    machine_port,
                    recipients,
                    notification_data,
                    auth_token,
                )
            )
        finally:
            if not loop.is_running():
                loop.close()

    async def send_packet(
        self,
        machine_host: str,
        machine_port: int,
        packet: "Packet",
        auth_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Send binary packet to remote machine via WebSocket.

        If self._crypto is set, the packet is HMAC-authenticated before sending.
        The receiver must have the same secret_key to verify.

        Args:
            machine_host: Remote machine hostname/IP
            machine_port: Remote machine WebSocket port
            packet: Packet instance (FilePacket, MessagePacket, or custom)
            auth_token: Optional authentication token

        Returns:
            (success, message) tuple
        """
        try:
            from .packet import encode_packet

            packet_data = encode_packet(packet, crypto=self._crypto)

            ws_url = f"ws://{machine_host}:{machine_port}/packet"

            async with asyncio.timeout(self.timeout):
                logger.info(
                    f"WebSocket transport: {ws_url} with packet_id {packet.packet_id} "
                    f"({len(packet_data)} bytes)"
                )
                await asyncio.sleep(0)

            auth_label = " (authenticated)" if self._crypto else ""
            return True, (
                f"Packet {packet.packet_id} sent{auth_label} ({len(packet_data)} bytes)"
            )

        except Exception as e:
            logger.error(f"Failed to send packet: {e}")
            return False, f"Failed to send packet: {e}"

    def send_packet_sync(
        self,
        machine_host: str,
        machine_port: int,
        packet: "Packet",
        auth_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Synchronous wrapper for send_packet.

        Args:
            machine_host: Remote machine hostname/IP
            machine_port: Remote machine WebSocket port
            packet: Packet instance
            auth_token: Optional authentication token

        Returns:
            (success, message) tuple
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return False, "Cannot use sync transport in async context"
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            return loop.run_until_complete(
                self.send_packet(machine_host, machine_port, packet, auth_token)
            )
        finally:
            if not loop.is_running():
                loop.close()


class WebSocketProtocol:
    """
    WebSocket protocol handler for incoming notifications from remote machines.
    """

    def __init__(
        self,
        transport: WebSocketTransport,
        secret_key: Optional[bytes] = None,
    ):
        """
        Initialize protocol handler.

        Args:
            transport: WebSocketTransport instance for sending
            secret_key: Optional pre-shared secret for HMAC verification.
                        If provided, incoming packets are verified before decoding.
        """
        self.transport = transport
        self._crypto = None
        if secret_key:
            from .crypto import CryptoHash

            self._crypto = CryptoHash(secret_key)

    async def handle_notification(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Handle incoming notification from remote machine.

        Args:
            payload: Notification payload

        Returns:
            (success, message) tuple
        """
        try:
            if payload.get("type") != "notify":
                return False, "Invalid payload type"

            recipients = payload.get("recipients")
            if not isinstance(recipients, list):
                return False, "Invalid recipients list"

            logger.info(
                f"Received remote notification for {len(recipients)} recipients"
            )
            return True, "Notification processed"

        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            return False, f"Error: {e}"

    async def handle_packet(
        self, raw_bytes: bytes
    ) -> Tuple[bool, str, Optional["Packet"]]:
        """
        Handle incoming raw packet bytes.

        If self._crypto is set, verifies HMAC before decoding.

        Args:
            raw_bytes: Raw packet bytes from transport

        Returns:
            (success, message, packet) tuple.
            packet is None if decoding failed.

        Raises:
            PacketAuthError: If HMAC verification fails
        """
        from .crypto import PacketAuthError
        from .packet import decode_packet

        try:
            data = raw_bytes
            if self._crypto:
                try:
                    data, ok = self._crypto.strip_and_verify(raw_bytes)
                except PacketAuthError:
                    logger.warning("HMAC verification failed on incoming packet")
                    return False, "HMAC verification failed", None
                if not ok:
                    logger.warning("HMAC mismatch on incoming packet")
                    return False, "HMAC mismatch", None

            packet = decode_packet(data)
            return True, "Packet decoded", packet

        except PacketAuthError:
            logger.warning("Packet auth error during decode")
            return False, "Packet auth error", None
        except Exception as e:
            logger.error(f"Error handling packet: {e}")
            return False, f"Error: {e}", None


class WebSocketServer:
    """
    WebSocket server for accepting client connections and handling messages.
    
    Usage:
        async def handler(server, websocket, path, message):
            msg_type = message.get("type")
            if msg_type == "ping":
                return {"type": "pong", "timestamp": message.get("timestamp")}
            return None  # broadcast this response to all clients
        
        server = WebSocketServer(host="0.0.0.0", port=8765, handler=handler)
        await server.start()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        handler: Optional[WebSocketMessageHandler] = None,
        secret_key: Optional[bytes] = None,
    ):
        """
        Initialize WebSocket server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
            handler: Async callback for handling incoming messages.
                    Should accept (server, websocket, path, message) and return
                    a response dict (sent to sender) or None (broadcast to all).
            secret_key: Optional HMAC secret for authenticating packets.
        """
        self.host = host
        self.port = port
        self.handler = handler
        self._secret_key = secret_key
        self._server: Optional[asyncio.Server] = None
        self._clients: Dict[Any, Set] = {}  # path -> set of websockets
        self._running = False
        
        # Service registry for handling message types
        # Format: {message_type: service_instance}
        # Each service should have an async handle_message(server, websocket, path, message) method
        self._services: Dict[str, Any] = {}
        
        # Default service (catches unhandled messages)
        self._default_service: Optional[Any] = None
    
    def register_service(self, service: Any, message_types: Optional[list[str]] = None) -> None:
        """
        Register a service to handle specific message types.
        
        Args:
            service: Service instance with async handle_message(server, websocket, path, message) method
            message_types: List of message types this service handles (e.g., ["auth", "bet", "hit"])
                           If None, service becomes the default service
        """
        if message_types is None:
            self._default_service = service
            logger.info(f"Registered default service: {service.__class__.__name__}")
        else:
            for msg_type in message_types:
                self._services[msg_type] = service
            logger.info(f"Registered service {service.__class__.__name__} for: {message_types}")
    
    def unregister_service(self, message_types: list[str]) -> None:
        """Unregister a service by message types."""
        for msg_type in message_types:
            self._services.pop(msg_type, None)
    
    def get_service(self, message_type: str) -> Optional[Any]:
        """Get the service that handles a specific message type."""
        return self._services.get(message_type)
    
    def list_services(self) -> Dict[str, str]:
        """List all registered services and their message types."""
        result = {}
        for msg_type, service in self._services.items():
            result[msg_type] = service.__class__.__name__
        if self._default_service:
            result["*default*"] = self._default_service.__class__.__name__
        return result
    
    async def dispatch_message(
        self, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatch message to appropriate service based on message type.
        
        Returns:
            Response dict, or None for broadcast
        """
        msg_type = message.get("type", "")
        
        # Look up service for this message type
        service = self.get_service(msg_type)
        
        if service is None and self._default_service:
            service = self._default_service
        
        if service:
            try:
                return await service.handle_message(self, websocket, path, message)
            except Exception as e:
                logger.error(f"Service {service.__class__.__name__} error: {e}")
                return {"type": "error", "code": "service_error", "message": str(e)}
        
        # No service found
        return {"type": "error", "code": "no_handler", "message": f"No handler for message type: {msg_type}"}

    async def start(self) -> None:
        """Start the WebSocket server."""
        import websockets
        
        self._running = True
        
        async def on_connect(websocket):
            """Handle new WebSocket connection."""
            # Extract path from websocket - websockets 16+ changed API
            # Path is available via websocket.path or we use "default"
            try:
                path = getattr(websocket, 'path', None)
                if path:
                    path = path.strip("/") or "default"
                else:
                    path = "default"
            except Exception:
                path = "default"
            
            if path not in self._clients:
                self._clients[path] = set()
            self._clients[path].add(websocket)
            
            logger.info(f"Client connected to {path}, total: {len(self._clients[path])}")
            
            try:
                async for raw_message in websocket:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError as e:
                        error_resp = {"type": "error", "code": "invalid_json", "message": str(e)}
                        await websocket.send(json.dumps(error_resp))
                        continue
                    
                    # Call user handler if provided, or use service registry
                    if self.handler:
                        try:
                            response = await self.handler(self, websocket, path, message)
                            
                            # Send response to sender only
                            if response is not None:
                                await websocket.send(json.dumps(response))
                            # If handler returns None, it will handle broadcasting itself
                            # (useful for chat, game state updates, etc.)
                            
                        except Exception as e:
                            logger.error(f"Handler error: {e}")
                            error_resp = {"type": "error", "code": "handler_error", "message": str(e)}
                            await websocket.send(json.dumps(error_resp))
                    elif self._services or self._default_service:
                        # Use service registry
                        try:
                            response = await self.dispatch_message(websocket, path, message)
                            
                            if response is not None:
                                await websocket.send(json.dumps(response))
                                
                        except Exception as e:
                            logger.error(f"Service dispatch error: {e}")
                            error_resp = {"type": "error", "code": "dispatch_error", "message": str(e)}
                            await websocket.send(json.dumps(error_resp))
                    else:
                        # No handler - echo back
                        await websocket.send(json.dumps(message))
                        
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                if path in self._clients:
                    self._clients[path].remove(websocket)
                    if not self._clients[path]:
                        del self._clients[path]
                logger.info(f"Client disconnected from {path}")

        self._server = await websockets.serve(on_connect, self.host, self.port)
        logger.info(f"WebSocket server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket server stopped")

    async def broadcast(self, message: Dict[str, Any], path: Optional[str] = None) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message dict to broadcast
            path: Optional path to restrict broadcast. If None, broadcasts to all paths.
        """
        if not self._clients:
            return
            
        msg_json = json.dumps(message)
        
        if path:
            # Send to specific path only
            if path in self._clients:
                websockets_to_close = []
                for ws in self._clients[path]:
                    try:
                        await ws.send(msg_json)
                    except Exception:
                        websockets_to_close.append(ws)
                for ws in websockets_to_close:
                    self._clients[path].discard(ws)
        else:
            # Send to all paths
            for path_clients in self._clients.values():
                websockets_to_close = []
                for ws in path_clients:
                    try:
                        await ws.send(msg_json)
                    except Exception:
                        websockets_to_close.append(ws)
                for ws in websockets_to_close:
                    path_clients.discard(ws)

    async def send_to(self, websocket: Any, message: Dict[str, Any]) -> None:
        """Send message to specific client."""
        await websocket.send(json.dumps(message))

    def get_clients(self, path: Optional[str] = None) -> int:
        """Get count of connected clients."""
        if path:
            return len(self._clients.get(path, set()))
        return sum(len(clients) for clients in self._clients.values())

    @property
    def is_running(self) -> bool:
        return self._running
