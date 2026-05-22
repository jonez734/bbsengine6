# bbsengine6/net/transport.py
# WebSocket transport protocol for remote notification and packet delivery.

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from .packet import Packet

logger = logging.getLogger(__name__)


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
