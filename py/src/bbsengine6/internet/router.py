# internet/router.py
# Routing logic for internet addresses.

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .address import AddressParser
from .transport import WebSocketTransport


class InternetRouter:
    """Route notifications between local and remote machines."""

    def __init__(self, local_machine: str = "local"):
        """
        Initialize router.

        Args:
            local_machine: Local machine identifier
        """
        self.parser = AddressParser(local_machine)
        self.transport = WebSocketTransport()
        self.local_machine = local_machine

    def route(
        self, addresses: List[str]
    ) -> Tuple[List[str], Dict[str, List[str]], Dict[str, str]]:
        """
        Route a list of addresses into local and remote recipients.

        Args:
            addresses: List of recipient addresses (mixed local and remote)

        Returns:
            (local_recipients, remote_recipients_by_machine, errors) tuple
            - local_recipients: List of local monikers
            - remote_recipients_by_machine: Dict[machine] -> List[recipients]
            - errors: Dict[address] -> error message
        """
        result = self.parser.parse_list(addresses)

        local_recipients = []
        remote_by_machine: Dict[str, List[str]] = {}

        # Sort parsed addresses
        for addr in result.valid:
            if addr.is_local():
                local_recipients.append(addr.user)
            else:
                machine = addr.machine
                if machine not in remote_by_machine:
                    remote_by_machine[machine] = []
                remote_by_machine[machine].append(addr.user)

        return local_recipients, remote_by_machine, result.invalid


# Module-level defaults
_default_router: Optional[InternetRouter] = None


def get_router(local_machine: str = "local") -> InternetRouter:
    """Get or create default internet router."""
    global _default_router
    if _default_router is None:
        _default_router = InternetRouter(local_machine)
    return _default_router


def route_recipients(
    addresses: List[str], local_machine: str = "local"
) -> Tuple[List[str], Dict[str, List[str]], Dict[str, str]]:
    """Route recipients into local and remote groups."""
    return get_router(local_machine).route(addresses)
