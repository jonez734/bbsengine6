# bbsengine6/net/__init__.py
# BBSEngine6 network layer: SMTP-like addressing + notification integration
# Video frame transmission code has been moved to asimov.net

# SMTP-like addressing (user@machine)
from .address import (
    AddressParser,
    AddressType,
    InternetAddress,
    is_internet_address,
    parse_address,
)

# Routing
from .router import InternetRouter, get_router, route_recipients

# Machine registry
from .registry import MachineConfig, MachineRegistry, get_registry

# WebSocket transport
from .transport import WebSocketProtocol, WebSocketTransport

# Integration layer
from .integration import NotifyIntegration, get_integration, send_with_internet


__all__ = [
    # SMTP-like addressing
    "AddressParser",
    "AddressType",
    "InternetAddress",
    "is_internet_address",
    "parse_address",
    
    # Routing
    "InternetRouter",
    "get_router",
    "route_recipients",
    
    # Machine registry
    "MachineConfig",
    "MachineRegistry",
    "get_registry",
    
    # WebSocket transport
    "WebSocketProtocol",
    "WebSocketTransport",
    
    # Integration
    "NotifyIntegration",
    "get_integration",
    "send_with_internet",
]
