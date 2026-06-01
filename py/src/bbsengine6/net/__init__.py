# bbsengine6/net/__init__.py
# BBSEngine6 network layer: SMTP-like addressing, packet system, notification integration

# SMTP-like addressing (user@machine)
from .address import (
    AddressParser,
    AddressType,
    InternetAddress,
    is_internet_address,
    parse_address,
)

# Frame addressing (DSN-style URI)
from .frame_address import (
    FrameAddress,
    FrameAddressParser,
    FrameScheme,
    ParseResult,
)

# Frame types (copied from asimov.net, not imported)
from .frame_types import (
    Frame,
    NumpyFrame,
    frame_from_any,
    frames_equal,
)

# TCP sender/receiver (copied from asimov.net, not imported)
from .tcp import (
    TCPSender,
    TCPReceiver,
)

# Packet system (Files, Messages, PING/PONG)
from .packet import (
    CHECKSUM_ALGORITHM,
    CHECKSUM_HEX_LEN,
    MAX_BLOCK_SIZE,
    MAX_PAYLOAD_SIZE,
    Packet,
    PacketChecksumError,
    PacketDecodeError,
    PacketTypeError,
    PACKET_TYPE_FILE,
    PACKET_TYPE_MESSAGE,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    decode_packet,
    encode_packet,
    get_packet_type,
    register_packet_type,
)

from .packet_types import FilePacket, MessagePacket, PingPacket, PongPacket

# HMAC authentication
from .crypto import CryptoHash, PacketAuthError, get_crypto

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
    # Frame addressing
    "FrameAddress",
    "FrameAddressParser",
    "FrameScheme",
    "ParseResult",
    # Frame types
    "Frame",
    "NumpyFrame",
    "frame_from_any",
    "frames_equal",
    # TCP sender/receiver
    "TCPSender",
    "TCPReceiver",
    # Packet system
    "Packet",
    "FilePacket",
    "MessagePacket",
    "PingPacket",
    "PongPacket",
    "PACKET_TYPE_FILE",
    "PACKET_TYPE_MESSAGE",
    "PACKET_TYPE_PING",
    "PACKET_TYPE_PONG",
    "MAX_BLOCK_SIZE",
    "MAX_PAYLOAD_SIZE",
    "CHECKSUM_ALGORITHM",
    "CHECKSUM_HEX_LEN",
    "encode_packet",
    "decode_packet",
    "get_packet_type",
    "register_packet_type",
    "PacketTypeError",
    "PacketDecodeError",
    "PacketChecksumError",
    # HMAC authentication
    "CryptoHash",
    "PacketAuthError",
    "get_crypto",
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
