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
from .integration import NotifyIntegration, get_integration, send_with_internet
from .registry import MachineConfig, MachineRegistry, get_registry
from .router import InternetRouter, get_router, route_recipients
from .transport import WebSocketProtocol, WebSocketTransport

__all__ = [
    "AddressParser",
    "AddressType",
    "InternetAddress",
    "ParseResult",
    "InternetRouter",
    "WebSocketTransport",
    "WebSocketProtocol",
    "NotifyIntegration",
    "MachineConfig",
    "MachineRegistry",
    "is_internet_address",
    "parse_address",
    "route_recipients",
    "get_integration",
    "send_with_internet",
    "get_router",
    "get_registry",
]
