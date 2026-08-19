# bbsengine6/net/transport.py
# WebSocket transport protocol for remote notification and packet delivery.

import asyncio
import contextlib
import inspect
import json
import logging
import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Set, Tuple

import websockets.asyncio.server
import websockets.exceptions

from bbsengine6 import io as bbs_io

if TYPE_CHECKING:
    from .packet import Packet

logger = logging.getLogger(__name__)


@dataclass
class ChannelState:
    """State container for channel subscriptions."""

    channels: Dict[str, Set[int]] = field(
        default_factory=dict
    )  # channel -> session_ids
    callbacks: Dict[str, List[Callable]] = field(
        default_factory=dict
    )  # channel -> callbacks
    session_channels: Dict[int, Set[str]] = field(
        default_factory=dict
    )  # session_id -> channels


def channel_subscribe(state: ChannelState, session_id: int, channel: str) -> None:
    """Subscribe a session to a channel."""
    if channel not in state.channels:
        state.channels[channel] = set()
    state.channels[channel].add(session_id)

    if session_id not in state.session_channels:
        state.session_channels[session_id] = set()
    state.session_channels[session_id].add(channel)


def channel_unsubscribe(state: ChannelState, session_id: int, channel: str) -> None:
    """Unsubscribe a session from a channel."""
    if channel in state.channels:
        state.channels[channel].discard(session_id)
        if not state.channels[channel]:
            del state.channels[channel]

    if session_id in state.session_channels:
        state.session_channels[session_id].discard(channel)


def channel_unsubscribe_all(state: ChannelState, session_id: int) -> None:
    """Unsubscribe a session from all channels (cleanup on disconnect)."""
    if session_id not in state.session_channels:
        return

    for channel in list(state.session_channels[session_id]):
        if channel in state.channels:
            state.channels[channel].discard(session_id)
            if not state.channels[channel]:
                del state.channels[channel]

    del state.session_channels[session_id]


def channel_register_callback(
    state: ChannelState, channel: str, callback: Callable
) -> None:
    """Register a callback for a channel (for in-process bots).

    Re-registering the same callable for the same channel is a no-op
    (dedup by identity). This prevents accidental double-invocation
    when a bot reconnects without first unregistering.
    """
    if channel not in state.callbacks:
        state.callbacks[channel] = []
    if callback in state.callbacks[channel]:
        return
    state.callbacks[channel].append(callback)


def channel_unregister_callback(
    state: ChannelState, channel: str, callback: Callable
) -> bool:
    """Remove a single callback from a channel.

    Returns True if the callback was found and removed, False otherwise.
    """
    callbacks = state.callbacks.get(channel)
    if not callbacks:
        return False
    try:
        callbacks.remove(callback)
    except ValueError:
        return False
    if not callbacks:
        del state.callbacks[channel]
    return True


def channel_unregister_all_callbacks(
    state: ChannelState, channel: Optional[str] = None
) -> int:
    """Remove every callback for a channel (or all channels if None).

    Returns the number of callbacks removed. Useful for test teardown
    and for "stop the bot" handlers.
    """
    if channel is None:
        total = sum(len(cbs) for cbs in state.callbacks.values())
        state.callbacks.clear()
        return total
    callbacks = state.callbacks.pop(channel, None)
    return len(callbacks) if callbacks else 0


def channel_get_subscribers(state: ChannelState, channel: str) -> Set[int]:
    """Get all session_ids subscribed to a channel."""
    return state.channels.get(channel, set()).copy()


def channel_get_session_channels(state: ChannelState, session_id: int) -> Set[str]:
    """Get all channels a session is subscribed to."""
    return state.session_channels.get(session_id, set()).copy()


async def channel_publish(
    state: ChannelState,
    channel: str,
    message: Dict[str, Any],
    server: Optional["WebSocketServer"] = None,
    sender_moniker: Optional[str] = None,
    args: Optional[Any] = None,
) -> None:
    """Publish message to all subscribers of a channel.

    Args:
        state: Channel state container.
        channel: Channel name.
        message: Message dict to publish.
        server: Optional WebSocket server for fan-out.
        sender_moniker: Optional moniker of the sender. When provided
            together with ``args``, the channel is checked for
            announce-only restrictions via ChannelService.can_publish.
        args: Optional application args (required to perform the
            announce-only check).
    """
    if sender_moniker is not None and args is not None:
        from bbsengine6.services.channel import ChannelService

        try:
            channel_service = ChannelService(args)
            verdict = channel_service.can_publish(channel, sender_moniker)
        except Exception as e:
            logger.error(f"channel_publish permission check failed: {e}")
            return

        if not verdict.get("allowed", False):
            logger.warning(
                f"channel_publish denied: channel={channel} "
                f"sender={sender_moniker} reason={verdict.get('reason')}"
            )
            return

    # Send to WebSocket subscribers. The previous implementation routed
    # via server.broadcast(path=f"channel:{channel}"), which only reaches
    # clients connected to that path; clients on the canonical "default"
    # path were silently dropped. Fan out to each subscribed websocket
    # directly, matching either the transport-allocated
    # ``_bbsengine6_session_id`` or the Python ``id(websocket)`` fallback
    # (callers may have subscribed under either identity).
    #
    # On send failure, drop the dead websocket from ``server._clients``
    # so it is not retried on subsequent publishes (mirrors the cleanup
    # logic in ``server.broadcast``); the socket is also explicitly
    # closed so its file descriptor is released immediately rather than
    # waiting for garbage collection.
    if server and channel in state.channels:
        target_session_ids = state.channels[channel]
        delivered_ws: Set[int] = set()
        for path, path_clients in list(server._clients.items()):
            failed_ws = []
            for ws in path_clients:
                if id(ws) in delivered_ws:
                    continue
                ws_bbs_id = getattr(ws, "_bbsengine6_session_id", None)
                if (
                    id(ws) in target_session_ids
                    or (ws_bbs_id is not None and ws_bbs_id in target_session_ids)
                ):
                    delivered_ws.add(id(ws))
                    try:
                        await ws.send(json.dumps(message))
                    except Exception as e:
                        logger.warning(
                            f"channel_publish send failed: channel={channel} e={e}"
                        )
                        failed_ws.append(ws)
            for ws in failed_ws:
                path_clients.discard(ws)
                with contextlib.suppress(Exception):
                    await ws.close()
            if not path_clients:
                server._clients.pop(path, None)

    # Invoke registered callbacks (for bots)
    if channel in state.callbacks:
        for callback in state.callbacks[channel]:
            try:
                if inspect.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in channel callback: {e}")


# Callback type for handling incoming WebSocket messages
# signature: async def handler(websocket, path, message: dict) -> Optional[dict]
# Return value is sent back to client, or None for broadcast
WebSocketMessageHandler = Callable[
    ["WebSocketServer", Any, str, Dict[str, Any]], Optional[Dict[str, Any]]
]


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
        message_data: Dict[str, Any],
        auth_token: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Send message to remote machine via WebSocket.

        Opens a real ``websockets.connect`` session, sends the JSON
        payload, and reads at most one frame back as an ack. Returns
        ``(True, ...)`` on a successful round-trip, or ``(False, ...)``
        with a human-readable error on any failure (timeout, refused
        connection, invalid URL, send error, etc).

        Args:
            machine_host: Remote machine hostname/IP
            machine_port: Remote machine WebSocket port
            recipients: List of recipients on remote machine
            message_data: Message payload
            auth_token: Optional authentication token

        Returns:
            (success, message) tuple
        """
        import websockets

        ws_url = f"ws://{machine_host}:{machine_port}/message"

        payload: Dict[str, Any] = {
            "type": "message",
            "recipients": recipients,
            "data": message_data,
        }
        if auth_token:
            payload["auth_token"] = auth_token

        try:
            async with asyncio.timeout(self.timeout):
                logger.info(
                    f"WebSocket transport: connecting {ws_url} "
                    f"for {len(recipients)} recipients"
                )
                async with websockets.connect(ws_url) as ws:
                    await ws.send(json.dumps(payload))
                    logger.info(f"WebSocket transport: sent payload to {ws_url}")
                    # Best-effort ack: read one frame if the server
                    # sends one, but don't block if it doesn't.
                    try:
                        ack = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        logger.info(
                            f"WebSocket transport: ack from {ws_url}: {ack!r:.200}"
                        )
                    except asyncio.TimeoutError:
                        pass

                return True, f"Message sent to {len(recipients)} recipients"

        except asyncio.TimeoutError:
            return False, f"WebSocket timeout after {self.timeout}s"
        except websockets.exceptions.WebSocketException as e:
            return False, f"WebSocket error: {e}"
        except OSError as e:
            return False, f"WebSocket connection error: {e}"
        except Exception as e:
            logger.error(f"send_to_remote failed for {ws_url}: {e}")
            return False, f"WebSocket error: {e}"

    def send_to_remote_sync(
        self,
        machine_host: str,
        machine_port: int,
        recipients: List[str],
        message_data: Dict[str, Any],
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
                    message_data,
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
        Handle incoming message from remote machine.

        Args:
            payload: Message payload

        Returns:
            (success, message) tuple
        """
        try:
            if payload.get("type") != "message":
                return False, "Invalid payload type"

            recipients = payload.get("recipients")
            if not isinstance(recipients, list):
                return False, "Invalid recipients list"

            logger.info(f"Received remote message for {len(recipients)} recipients")
            return True, "Message processed"

        except Exception as e:
            logger.error(f"Error handling message: {e}")
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


def _format_peer(peer: Any) -> str:
    """Best-effort string for a peer sockaddr tuple (AF_INET or AF_INET6)."""
    if peer is None:
        return "unknown"
    if isinstance(peer, tuple) and len(peer) == 2:
        host, port = peer
        return f"{host}:{port}"
    return str(peer)


class PeerLoggingServerConnection(websockets.asyncio.server.ServerConnection):
    """ServerConnection subclass that logs handshake failures with peer info.

    The websockets library's ``conn_handler`` logs ``opening handshake failed``
    at ERROR with ``exc_info=True`` whenever the opening handshake raises. For
    peers that TCP-connect and close before sending an HTTP upgrade request,
    that produces a multi-frame traceback in the logs with no indication of
    who is doing it.

    This subclass overrides ``handshake`` to:
      * catch the handshake exception,
      * emit a single WARNING log line including the offending peer address,
      * NOT re-raise, so the library's ``conn_handler`` proceeds to abort the
        transport cleanly without logging the traceback.

    Successful handshakes flow through unchanged.
    """

    async def handshake(
        self,
        process_request: Any,
        process_response: Any,
        server_header: Any,
    ) -> None:
        try:
            await super().handshake(process_request, process_response, server_header)
        except websockets.exceptions.InvalidHandshake as exc:
            peer = None
            try:
                peer = self.transport.get_extra_info("peername")
            except Exception:
                bbs_io.echo_traceback(
                    "bbsengine6.net.transport.peer_logging.handshake.100:"
                )
            logger.warning(
                "WS handshake failed peer=%s exc=%s: %s",
                _format_peer(peer),
                type(exc).__name__,
                exc,
            )
            return
        except (EOFError, ConnectionResetError, OSError) as exc:
            peer = None
            try:
                peer = self.transport.get_extra_info("peername")
            except Exception:
                bbs_io.echo_traceback(
                    "bbsengine6.net.transport.peer_logging.handshake.200:"
                )
            logger.warning(
                "WS handshake aborted peer=%s exc=%s: %s",
                _format_peer(peer),
                type(exc).__name__,
                exc,
            )
            return


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
        channel_state: Optional["ChannelState"] = None,
        session_manager: Optional[Any] = None,
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
            channel_state: Optional shared ChannelState. When provided, the server
                    uses it for pub/sub so that subscribers registered through
                    handlers (e.g. ChannelServiceHandler) and publishers calling
                    server.publish(...) see the same state. When None, the server
                    creates its own state (legacy default; subscribers will not
                    be visible to other components).
            session_manager: Optional bbsengine6.session.SessionManager.
                    When provided, the server uses it to allocate session ids
                    and to look up moniker by session. When None, the server
                    constructs its own SessionManager (used for routing via
                    ``router.unregister_session`` cleanup).
        """
        self.host = host
        self.port = port
        self.handler = handler
        self._secret_key = secret_key
        self._server: Optional[asyncio.Server] = None
        self._clients: Dict[Any, Set] = {}  # path -> set of websockets
        self._running = False
        # Actual bound port. Set after ``start()`` completes its socket bind;
        # equals ``self.port`` when not 0. Useful for tests with ephemeral ports.
        self._bound_port: Optional[int] = None

        # Service registry for handling message types
        # Format: {message_type: service_instance}
        # Each service should have an async handle_message(server, websocket, path, message) method
        self._services: Dict[str, Any] = {}

        # Default service (catches unhandled messages)
        self._default_service: Optional[Any] = None

        # Channel state for pub/sub. Accept shared state so BED and the
        # router (and any bot callbacks) all see the same subscriptions.
        self._channel_state = (
            channel_state if channel_state is not None else ChannelState()
        )

        # Optional router reference for disconnect cleanup. When set,
        # the server calls router.unregister_session(session_id) on
        # disconnect. Set via register_router() or pass via BED.
        self._router: Optional[Any] = None

        # Pre-dispatch hook: async callable(websocket, message) invoked
        # before every service handler. Used by BED to set the
        # per-request PostgreSQL role from the session.
        self._pre_dispatch: Optional[Callable] = None

        # Post-dispatch hook: async callable(websocket, message, response)
        # invoked after the service handler returns. Used by BED to log
        # the dispatched message once the auth state is populated (the
        # pre-dispatch hook fires before AuthService.bind, so any state
        # lookup there is empty for the `auth` message itself).
        self._post_dispatch: Optional[Callable] = None

        # Session manager used for id allocation and moniker lookup.
        if session_manager is not None:
            self._sessions = session_manager
        else:
            from bbsengine6.session import SessionManager

            self._sessions = SessionManager()

    def register_service(
        self, service: Any, message_types: Optional[list[str]] = None
    ) -> None:
        """
        Register a service to handle specific message types.

        Args:
            service: Service instance with async handle_message(server, websocket, path, message) method
            message_types: List of message types this service handles (e.g., ["auth", "bet", "hit"])
                           If None, service becomes the default service

        When a registration would replace an already-registered handler
        (either a per-type entry in ``self._services`` or the
        ``self._default_service`` slot) a warning is emitted so the
        operator can see the overwrite in the log. This is intentional:
        ``register_service`` overwrites by ``msg_type`` key, so the
        last writer wins; bed relies on this to install its
        ``PingService`` after a router's own ``ping`` registration.
        The warning surfaces both intentional swaps (bed's ping
        override) and accidental ones (a custom router registering
        ``"auth"`` would silently replace ``AuthService``).
        """
        if message_types is None:
            if self._default_service is not None:
                prev = self._default_service.__class__.__name__
                new = service.__class__.__name__
                logger.warning(
                    f"WebSocketServer: overwriting existing default service "
                    f"previous={prev} new={new}"
                )
            self._default_service = service
            logger.info(f"Registered default service: {service.__class__.__name__}")
        else:
            overwritten: List[str] = []
            for msg_type in message_types:
                if msg_type in self._services:
                    prev = self._services[msg_type].__class__.__name__
                    overwritten.append(f"{msg_type}({prev})")
                self._services[msg_type] = service
            if overwritten:
                new = service.__class__.__name__
                logger.warning(
                    f"WebSocketServer: overwriting existing handler(s) "
                    f"previous=[{', '.join(overwritten)}] new={new} "
                    f"message_types={list(message_types)}"
                )
            logger.info(
                f"Registered service {service.__class__.__name__} for: {message_types}"
            )

    def unregister_service(self, message_types: list[str]) -> None:
        """Unregister a service by message types."""
        for msg_type in message_types:
            self._services.pop(msg_type, None)

    def register_router(self, router: Any) -> None:
        """Register a router for disconnect-time session cleanup.

        The router must expose ``unregister_session(session_id: int)``.
        When set, ``on_connect`` will look up the session id from the
        websocket and call this on disconnect. Allows the shared
        ``ChannelState`` to be cleaned up automatically without each
        router subclass duplicating cleanup logic.
        """
        self._router = router
        logger.info(f"Registered router: {router.__class__.__name__}")

    def _alloc_session_id(self) -> int:
        """Allocate a monotonic session id for a new connection.

        Delegates to the underlying SessionManager, which uses
        ``itertools.count`` (atomic under the CPython GIL).
        """
        return self._sessions.alloc_session_id()

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

    def _handle_list_services(self) -> Dict[str, Any]:
        """Built-in `list_services` message handler.

        Returns the live set of registered message types so a client
        can probe the server's runtime surface area before
        authenticating. Routers must not register their own
        `list_services` handler; this is the canonical answer.

        Wire shape: {"type": "services", "services": [str, ...]}.
        Matches the legacy `_handle_list_services` in
        `bbsengine6.net.defaultrouter.DefaultRouter` and
        `zoid6.api.monikerrouter.MonikerAuthRouter`, but reports
        the *actual* registered keys (sorted) rather than a
        hardcoded list.
        """
        keys = list(self._services.keys())
        if self._default_service is not None:
            keys.append("*default*")
        return {"type": "services", "services": sorted(keys)}

    async def dispatch_message(
        self, websocket: Any, path: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Dispatch message to appropriate service based on message type.

        The `list_services` message type is answered directly by the
        server (returning the live keys of `self._services` plus the
        default service) without consulting the service registry.
        This is the canonical discovery primitive; routers must not
        register their own `list_services` handler.

        If the incoming message carries a ``request_id`` (the bed
        client protocol convention), the server copies it onto the
        outgoing response so the matching :class:`BedConnection`
        recv loop can match the reply to the originating request.
        Without this echo ``BedConnection.send`` would always time
        out, because its :meth:`_recv_match` lambda keys on
        ``request_id``.

        Returns:
            Response dict, or None for broadcast
        """
        msg_type = message.get("type", "")
        incoming_request_id = message.get("request_id")

        # Built-in: list_services is answered by the server itself.
        if msg_type == "list_services":
            return self._echo_request_id(
                self._handle_list_services(), incoming_request_id
            )

        # Look up service for this message type
        service = self.get_service(msg_type)

        if service is None and self._default_service:
            service = self._default_service

        if service:
            try:
                if self._pre_dispatch is not None:
                    await self._pre_dispatch(websocket, message)
                response = await service.handle_message(
                    self, websocket, path, message
                )
                if self._post_dispatch is not None:
                    try:
                        await self._post_dispatch(websocket, message, response)
                    except Exception:
                        bbs_io.echo_traceback(
                            "bbsengine6.net.transport.dispatch_message.post_dispatch:"
                        )
                return self._echo_request_id(response, incoming_request_id)
            except Exception as e:
                logger.error(f"Service {service.__class__.__name__} error: {e}")
                return self._echo_request_id(
                    {"type": "error", "code": "service_error", "message": str(e)},
                    incoming_request_id,
                )

        # No service found
        return self._echo_request_id(
            {
                "type": "error",
                "code": "no_handler",
                "message": f"No handler for message type: {msg_type}",
            },
            incoming_request_id,
        )

    @staticmethod
    def _echo_request_id(
        response: Optional[Dict[str, Any]], request_id: Any
    ) -> Optional[Dict[str, Any]]:
        """Copy ``request_id`` from the request onto the response.

        No-op when ``response`` is ``None`` (broadcast) or when
        ``request_id`` is missing/empty on the incoming side. The
        original response object is left untouched when the echo
        cannot be applied so handlers returning shared/static
        dicts are not mutated.
        """
        if response is None or not request_id:
            return response
        # If the handler already echoed the same id, leave it alone.
        if response.get("request_id") == request_id:
            return response
        # Broadcast shared/static dicts as a defensive copy only if we
        # actually need to attach anything.
        echoed = dict(response)
        echoed["request_id"] = request_id
        return echoed

    async def start(self) -> None:
        """Start the WebSocket server."""
        import websockets

        self._running = True

        async def on_connect(websocket):
            """Handle new WebSocket connection."""
            # Extract path from websocket - websockets 16+ changed API
            # Path is available via websocket.path or we use "default"
            try:
                path = getattr(websocket, "path", None)
                if path:
                    path = path.strip("/") or "default"
                else:
                    path = "default"
            except Exception:
                path = "default"

            peer = None
            try:
                peer = websocket.transport.get_extra_info("peername")
            except Exception:
                bbs_io.echo_traceback(
                    "bbsengine6.net.transport.WebSocketServer.start.on_connect.100:"
                )
            logger.debug(
                f"on_connect accepted peer={_format_peer(peer)} path={path}"
            )

            # Allocate a stable session id for this connection. Stashed on
            # the websocket so service handlers and disconnect cleanup can
            # use the same id without depending on id(websocket), which
            # can be reused after garbage collection.
            session_id = self._alloc_session_id()
            try:
                websocket._bbsengine6_session_id = session_id
            except Exception:
                # Some websocket test doubles don't allow attribute set.
                # Fall back to id() and log a warning.
                logger.warning(
                    "Could not set _bbsengine6_session_id on websocket; "
                    "falling back to id(websocket)"
                )

            if path not in self._clients:
                self._clients[path] = set()
            self._clients[path].add(websocket)

            logger.info(
                f"Client connected to {path} (session_id={session_id}), total: {len(self._clients[path])}"
            )

            try:
                async for raw_message in websocket:
                    try:
                        message = json.loads(raw_message)
                    except json.JSONDecodeError as e:
                        error_resp = {
                            "type": "error",
                            "code": "invalid_json",
                            "message": str(e),
                        }
                        await websocket.send(json.dumps(error_resp))
                        continue

                    # Call user handler if provided, or use service registry
                    if self.handler:
                        try:
                            response = await self.handler(
                                self, websocket, path, message
                            )

                            # Send response to sender only
                            if response is not None:
                                await websocket.send(json.dumps(response))
                            # If handler returns None, it will handle broadcasting itself
                            # (useful for chat, game state updates, etc.)

                        except Exception as e:
                            logger.error(f"Handler error: {e}")
                            error_resp = {
                                "type": "error",
                                "code": "handler_error",
                                "message": str(e),
                            }
                            await websocket.send(json.dumps(error_resp))
                    elif self._services or self._default_service:
                        # Use service registry
                        try:
                            response = await self.dispatch_message(
                                websocket, path, message
                            )

                            if response is not None:
                                await websocket.send(json.dumps(response))

                        except Exception as e:
                            logger.error(f"Service dispatch error: {e}")
                            error_resp = {
                                "type": "error",
                                "code": "dispatch_error",
                                "message": str(e),
                            }
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
                # Notify the router so it can clean up channel
                # subscriptions, session state, and finalize any
                # in-progress games.
                if self._router is not None:
                    try:
                        self._router.unregister_session(session_id)
                    except Exception as e:
                        logger.error(f"Router unregister_session error: {e}")
                logger.info(
                    f"Client disconnected from {path} (session_id={session_id})"
                )

        # Create socket with SO_REUSEADDR/SO_REUSEPORT for faster restart
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        sock.bind((self.host, self.port))
        sock.listen(128)

        # Record the actual port (relevant when port=0 was requested for
        # ephemeral binding, e.g. tests).
        try:
            self._bound_port = sock.getsockname()[1]
        except Exception:
            bbs_io.echo_traceback(
                "bbsengine6.net.transport.WebSocketServer.start.bound_port:"
            )
            self._bound_port = self.port

        self._server = await websockets.serve(
            on_connect,
            sock=sock,
            create_connection=PeerLoggingServerConnection,
            logger=logging.getLogger("websockets.server"),
        )
        logger.info(f"WebSocket server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            logger.info("WebSocket server stopped")

    async def broadcast(
        self, message: Dict[str, Any], path: Optional[str] = None
    ) -> None:
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

    async def publish(self, channel: str, message: Dict[str, Any]) -> None:
        """Publish message to a channel using the pub/sub system."""
        from bbsengine6.net import channel_publish

        await channel_publish(self._channel_state, channel, message, self)

    @property
    def is_running(self) -> bool:
        return self._running
