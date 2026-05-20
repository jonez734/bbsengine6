# bbsengine6/net/__init__.py
# Unified network layer: SMTP-like inter-machine addressing + frame transmission

# Configuration
from .conf import (
    CHUNK_SIZE,
    DEFAULT_PORT,
    COMPRESSION_ENABLED,
    BUFFER_SIZE,
    TCP_BUFFER_SIZE,
    UDP_BUFFER_SIZE,
    RETRY_DELAY,
    RETRY_COUNT,
)

# Socket utilities
from .socket import (
    recv_all,
    recv_udp,
    send_with_length,
    recv_with_length,
    retry_until_connected,
)

# Generic packet protocol
from .packet import (
    Packet,
    NetError,
    PacketTypeError,
    PING,
    PONG,
    EOS,
    encode_packet,
    decode_packet,
    register_packet_type,
)

# Frame packet protocol
from .frame import (
    FramePacket,
    encode_frame_header,
    encode_frame_packet,
    decode_frame_packet,
)

# Frame types (bytes and numpy)
from .frame_types import (
    Frame,
    NumpyFrame,
    frame_from_any,
    frames_equal,
)

# Frame addressing (DSN-like URIs)
from .frame_address import (
    FrameScheme,
    FrameAddress,
    FrameAddressParser,
    ParseResult,
    default_port_for_scheme,
)

# TCP transport
from .tcp import TCPSender, TCPReceiver

# UDP transport
from .udp import UDPSender, UDPReceiver

# SMTP-like addressing (existing)
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
    # Configuration
    "CHUNK_SIZE",
    "DEFAULT_PORT",
    "COMPRESSION_ENABLED",
    "BUFFER_SIZE",
    "TCP_BUFFER_SIZE",
    "UDP_BUFFER_SIZE",
    "RETRY_DELAY",
    "RETRY_COUNT",
    
    # Socket utilities
    "recv_all",
    "recv_udp",
    "send_with_length",
    "recv_with_length",
    "retry_until_connected",
    
    # Generic packet protocol
    "Packet",
    "NetError",
    "PacketTypeError",
    "PING",
    "PONG",
    "EOS",
    "encode_packet",
    "decode_packet",
    "register_packet_type",
    
    # Frame packet protocol
    "FramePacket",
    "encode_frame_header",
    "encode_frame_packet",
    "decode_frame_packet",
    
    # Frame types
    "Frame",
    "NumpyFrame",
    "frame_from_any",
    "frames_equal",
    
    # Frame addressing
    "FrameScheme",
    "FrameAddress",
    "FrameAddressParser",
    "ParseResult",
    "default_port_for_scheme",
    
    # TCP/UDP transport
    "TCPSender",
    "TCPReceiver",
    "UDPSender",
    "UDPReceiver",
    
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
