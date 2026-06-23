# bbsengine6/net/router.py
# Routing logic for internet addresses (notifications)

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .address import AddressParser
from .registry import MachineRegistry, get_registry
from .transport import WebSocketTransport

logger = logging.getLogger(__name__)

_default_router: Optional[InternetRouter] = None


class InternetRouter:
    """Route notifications between local and remote machines."""

    def __init__(
        self,
        local_machine: str = "local",
        registry: Optional[MachineRegistry] = None,
    ):
        """Initialize router."""
        self.parser = AddressParser(local_machine)
        self.transport = WebSocketTransport()
        self.local_machine = local_machine
        self.registry = registry or get_registry()

    def route(self, addresses: List[str]) -> Tuple[List[str], Dict[str, List[str]], Dict[str, Any], Dict[str, str]]:
        """Route addresses to local/remote recipients. Frame routing moved to asimov.net."""
        local_recipients = []
        remote_by_machine: Dict[str, List[str]] = {}
        frame_addresses: Dict[str, Any] = {}
        errors: Dict[str, str] = {}

        for address in addresses:
            notif_result = self.parser.parse(address)
            if notif_result is None:
                errors[address] = "Invalid notification address"
            else:
                if notif_result.is_local():
                    local_recipients.append(notif_result.user)
                else:
                    machine = notif_result.machine
                    if machine not in remote_by_machine:
                        remote_by_machine[machine] = []
                    remote_by_machine[machine].append(notif_result.user)

        # TODO: Add frame support via asimov.net when needed:
        # from asimov.net import FrameAddress, FrameAddressParser
        # frame_parser = FrameAddressParser()
        # for address in addresses:
        #     result = frame_parser.parse(address)
        #     if result.success:
        #         frame_addresses[address] = result.value

        return local_recipients, remote_by_machine, frame_addresses, errors

    async def send_notification(self, message: Dict[str, Any], recipients: List[str]) -> Dict[str, Any]:
        """Send notification to local recipients."""
        results = {}
        for recipient in recipients:
            try:
                from bbsengine6 import notify
                notify.notify(
                    recipient,
                    message.get("body", ""),
                    message.get("subject", ""),
                    message.get("priority", "normal"),
                )
                results[recipient] = "ok"
            except Exception as e:
                results[recipient] = str(e)
        return results


def get_router(local_machine: str = "local", registry: Optional[MachineRegistry] = None) -> InternetRouter:
    """Get or create default internet router."""
    global _default_router
    if _default_router is None:
        _default_router = InternetRouter(local_machine, registry)
    return _default_router


def route_recipients(addresses: List[str], local_machine: str = "local") -> Tuple[List[str], Dict[str, List[str]], Dict[str, Any], Dict[str, str]]:
    """Route recipients into local and remote groups."""
    return get_router(local_machine).route(addresses)
