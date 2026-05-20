# internet/address.py
# Address parsing and validation for internet layer.

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

# Address format: user@machine or user@machine.example.com
_ADDRESS_PATTERN = r"^([a-zA-Z0-9._%-]+)@([a-zA-Z0-9.-]+)$"


class AddressType(Enum):
    """Classification of an internet address."""

    LOCAL = "local"
    REMOTE = "remote"
    FEDERATED = "federated"


@dataclass
class InternetAddress:
    """Parsed internet address (user@machine)."""

    user: str
    machine: str
    full_address: str
    address_type: AddressType

    def __str__(self) -> str:
        return self.full_address

    def is_local(self) -> bool:
        return self.address_type == AddressType.LOCAL

    def is_remote(self) -> bool:
        return self.address_type == AddressType.REMOTE

    def is_federated(self) -> bool:
        return self.address_type == AddressType.FEDERATED


@dataclass
class ParseResult:
    """Result of parsing a recipient list."""

    valid: List[InternetAddress]
    invalid: Dict[str, str]


class AddressParser:
    """Parse and validate internet addresses."""

    def __init__(self, local_machine: str = "local"):
        """
        Initialize parser with local machine name.

        Args:
            local_machine: Local machine identifier (default: "local")
        """
        self.local_machine = local_machine
        self._pattern = re.compile(_ADDRESS_PATTERN)

    def parse(self, address: str) -> Optional[InternetAddress]:
        """
        Parse a single internet address.

        Args:
            address: Address string (e.g., "alice@machine1")

        Returns:
            InternetAddress if valid, None if invalid
        """
        address = address.strip()
        match = self._pattern.match(address)
        if not match:
            return None

        user, machine = match.groups()

        # Classify address type
        if machine.lower() == self.local_machine.lower():
            addr_type = AddressType.LOCAL
        elif "." not in machine:
            addr_type = AddressType.REMOTE
        else:
            addr_type = AddressType.FEDERATED

        return InternetAddress(
            user=user,
            machine=machine,
            full_address=address,
            address_type=addr_type,
        )

    def parse_list(self, addresses: List[str]) -> ParseResult:
        """
        Parse a list of addresses, separating valid from invalid.

        Args:
            addresses: List of address strings

        Returns:
            ParseResult with valid and invalid addresses
        """
        valid = []
        invalid = {}

        for address in addresses:
            parsed = self.parse(address)
            if parsed:
                valid.append(parsed)
            else:
                invalid[address] = "Invalid address format (expected user@machine)"

        return ParseResult(valid=valid, invalid=invalid)

    def is_internet_address(self, address: str) -> bool:
        """Check if address looks like an internet address (contains @)."""
        return "@" in address and self.parse(address) is not None


# Module-level defaults
_default_parser: Optional[AddressParser] = None


def get_parser(local_machine: str = "local") -> AddressParser:
    """Get or create default address parser."""
    global _default_parser
    if _default_parser is None:
        _default_parser = AddressParser(local_machine)
    return _default_parser


def is_internet_address(address: str, local_machine: str = "local") -> bool:
    """Check if address is an internet address."""
    return get_parser(local_machine).is_internet_address(address)


def parse_address(
    address: str, local_machine: str = "local"
) -> Optional[InternetAddress]:
    """Parse a single internet address."""
    return get_parser(local_machine).parse(address)
