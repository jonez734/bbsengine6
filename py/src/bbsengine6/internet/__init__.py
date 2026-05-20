# internet/__init__.py
# Internet layer for bbsengine6: SMTP-like inter-machine addressing.

from .address import (
    AddressParser,
    AddressType,
    InternetAddress,
    ParseResult,
    is_internet_address,
    parse_address,
)
from .router import InternetRouter, route_recipients
from .transport import WebSocketTransport

__all__ = [
    "AddressParser",
    "AddressType",
    "InternetAddress",
    "ParseResult",
    "InternetRouter",
    "WebSocketTransport",
    "is_internet_address",
    "parse_address",
    "route_recipients",
]
