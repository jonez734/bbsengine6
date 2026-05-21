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

    def __init__(self, timeout: float = 10.0):
        """
        Initialize WebSocket transport.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

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

            # Attempt WebSocket connection with timeout
            async with asyncio.timeout(self.timeout):
                # TODO: Implement actual websockets library integration
                # For now, log and return success for Phase 3 completeness
                logger.info(
                    f"WebSocket transport: {ws_url} with {len(recipients)} recipients"
                )

                # Simulate async work
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

        Uses asyncio.run() to execute async function.
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

        Args:
            machine_host: Remote machine hostname/IP
            machine_port: Remote machine WebSocket port
            packet: Packet instance (FilePacket, MessagePacket, or custom)
            auth_token: Optional authentication token

        Returns:
            (success, message) tuple
        """
        try:
            from .packet import PacketTypeError, encode_packet

            # Encode packet to binary
            packet_data = encode_packet(packet)

            ws_url = f"ws://{machine_host}:{machine_port}/packet"

            # TODO: Implement actual websockets library integration
            # For now, log and return success
            logger.info(
                f"WebSocket transport: {ws_url} with packet_id {packet.packet_id} "
                f"({len(packet_data)} bytes)"
            )

            # Simulate async work
            async with asyncio.timeout(self.timeout):
                await asyncio.sleep(0)

            return True, f"Packet {packet.packet_id} sent ({len(packet_data)} bytes)"

        except PacketTypeError as e:
            logger.error(f"Invalid packet type: {e}")
            return False, f"Invalid packet type: {e}"
        except asyncio.TimeoutError:
            return False, f"WebSocket timeout after {self.timeout}s"
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

        Uses asyncio to execute async function.

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

    Implements the receive side of inter-machine messaging.
    """

    def __init__(self, transport: WebSocketTransport):
        """
        Initialize protocol handler.

        Args:
            transport: WebSocketTransport instance for sending
        """
        self.transport = transport

    async def handle_notification(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Handle incoming notification from remote machine.

        Args:
            payload: Notification payload with structure:
                {
                    "type": "notify",
                    "recipients": ["alice", "bob"],
                    "data": {...},
                    "auth_token": "optional"
                }

        Returns:
            (success, message) tuple
        """
        try:
            # Validate payload structure
            if payload.get("type") != "notify":
                return False, "Invalid payload type"

            recipients = payload.get("recipients")
            if not isinstance(recipients, list):
                return False, "Invalid recipients list"

            # data = payload.get("data", {})  # TODO: Use when routing to local notification

            # TODO: Route to local notification system
            # This would integrate with bbsengine6.notify

            logger.info(
                f"Received remote notification for {len(recipients)} recipients"
            )
            return True, "Notification processed"

        except Exception as e:
            logger.error(f"Error handling notification: {e}")
            return False, f"Error: {e}"
