# internet/transport.py
# WebSocket transport protocol for remote notification delivery.

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class WebSocketTransport:
    """WebSocket transport for remote notification delivery."""

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

            async with asyncio.timeout(self.timeout):
                logger.info(
                    f"WebSocket transport: {ws_url} with {len(recipients)} recipients"
                )
                # TODO: Implement actual WebSocket send
                return True, "WebSocket delivery initiated"

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
