# bbsengine6/net/router.py
# Routing logic for internet addresses (notifications) and frame addresses

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .address import AddressParser
from asimov.net import FrameAddress, FrameAddressParser
from .registry import MachineRegistry, get_registry
from .transport import WebSocketTransport

logger = logging.getLogger(__name__)


class InternetRouter:
    """Route notifications and frames between local and remote machines."""

    def __init__(
        self,
        local_machine: str = "local",
        registry: Optional[MachineRegistry] = None,
    ):
        """
        Initialize router.

        Args:
            local_machine: Local machine identifier
            registry: MachineRegistry for remote machine configs
        """
        self.parser = AddressParser(local_machine)
        self.frame_parser = FrameAddressParser()
        self.transport = WebSocketTransport()
        self.local_machine = local_machine
        self.registry = registry or get_registry()

    def route(
        self, addresses: List[str]
    ) -> Tuple[
        List[str], Dict[str, List[str]], Dict[str, FrameAddress], Dict[str, str]
    ]:
        """
        Route a list of addresses into local, remote, and frame recipients.

        Args:
            addresses: List of recipient addresses (mixed notification and frame)

        Returns:
            (local_recipients, remote_recipients_by_machine, frame_addresses, errors) tuple
            - local_recipients: List of local notification monikers
            - remote_recipients_by_machine: Dict[machine] -> List[recipients] for notifications
            - frame_addresses: Dict[address_str] -> FrameAddress for frame transmission
            - errors: Dict[address] -> error message
        """
        local_recipients = []
        remote_by_machine: Dict[str, List[str]] = {}
        frame_addresses: Dict[str, FrameAddress] = {}
        errors: Dict[str, str] = {}

        for address in addresses:
            # Try to parse as frame address first (tcp://, udp://, etc.)
            frame_result = self.frame_parser.parse(address)

            if frame_result.success:
                # It's a frame address
                frame_addresses[address] = frame_result.value
            else:
                # Try as notification address (SMTP-like)
                notif_result = self.parser.parse(address)

                if notif_result is None:
                    # Both parse attempts failed
                    errors[address] = (
                        f"Invalid address (neither frame nor notification format)"
                    )
                else:
                    # Successfully parsed as notification address
                    if notif_result.is_local():
                        local_recipients.append(notif_result.user)
                    else:
                        machine = notif_result.machine
                        if machine not in remote_by_machine:
                            remote_by_machine[machine] = []
                        remote_by_machine[machine].append(notif_result.user)

        return local_recipients, remote_by_machine, frame_addresses, errors

    def get_machine_config(self, machine_name: str) -> Optional[Any]:
        """
        Get configuration for a remote machine.

        Args:
            machine_name: Machine identifier

        Returns:
            MachineConfig if found, None otherwise
        """
        config = self.registry.get(machine_name)
        if not config:
            logger.warning(f"No registry entry for machine: {machine_name}")
        return config

    def resolve_machine(
        self, machine_name: str
    ) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """
        Resolve machine name to connection details.

        Args:
            machine_name: Machine identifier

        Returns:
            (host, port, auth_token) tuple or (None, None, None) if not found
        """
        config = self.get_machine_config(machine_name)
        if config:
            return config.host, config.port, config.auth_token
        return None, None, None

    def classify_address(self, address: str) -> str:
        """
        Classify an address as 'frame', 'notification', or 'invalid'.

        Args:
            address: Address string to classify

        Returns:
            One of: 'frame', 'notification', 'invalid'
        """
        frame_result = self.frame_parser.parse(address)
        if frame_result.success:
            return "frame"

        notif_result = self.parser.parse(address)
        if address not in notif_result.invalid:
            return "notification"

        return "invalid"


# Module-level defaults
_default_router: Optional[InternetRouter] = None


def get_router(
    local_machine: str = "local", registry: Optional[MachineRegistry] = None
) -> InternetRouter:
    """Get or create default internet router."""
    global _default_router
    if _default_router is None:
        _default_router = InternetRouter(local_machine, registry)
    return _default_router


def route_recipients(
    addresses: List[str], local_machine: str = "local"
) -> Tuple[List[str], Dict[str, List[str]], Dict[str, FrameAddress], Dict[str, str]]:
    """
    Route recipients into local, remote, and frame groups.

    Returns:
        (local_recipients, remote_by_machine, frame_addresses, errors) tuple
    """
    return get_router(local_machine).route(addresses)
