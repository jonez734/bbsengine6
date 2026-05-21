# bbsengine6/net/packet.py
# Unified packet system for Files and Messages with block support, compression, and checksums

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Packet type constants
PACKET_TYPE_FILE = 10
PACKET_TYPE_MESSAGE = 11

# Size constraints
MAX_BLOCK_SIZE = 1_048_576  # 1 MB per block
MAX_PAYLOAD_SIZE = 1_048_576  # 1 MB total per-packet payload

# Checksum settings
CHECKSUM_ALGORITHM = "sha256"
CHECKSUM_HEX_LEN = 64  # SHA256 produces 64 hex characters

# Packet type registry for extensibility
_packet_type_registry: Dict[int, type] = {}


class PacketTypeError(ValueError):
    """Raised when packet type is unknown or invalid."""

    pass


class PacketDecodeError(ValueError):
    """Raised when packet data is malformed or cannot be decoded."""

    pass


class PacketChecksumError(ValueError):
    """Raised when packet checksum verification fails."""

    pass


def register_packet_type(packet_class: type) -> type:
    """
    Register a packet class for dynamic decoding.

    Args:
        packet_class: Class with packet_type attribute

    Returns:
        The packet_class (allows use as decorator)
    """
    if hasattr(packet_class, "packet_type"):
        _packet_type_registry[packet_class.packet_type] = packet_class
    return packet_class


@dataclass
class Packet:
    """
    Base packet class with common fields.

    All packets contain blocks (payload chunks), optional compression,
    and SHA256 checksums for integrity verification.
    """

    packet_type: int
    timestamp: float = field(default_factory=time.time)
    packet_id: int = 0
    blocks: List[bytes] = field(default_factory=list)
    block_sizes: Optional[List[int]] = None
    blocks_in_packet: int = 1
    compressed: bool = False
    checksum: Optional[str] = None  # SHA256 as hex string (64 chars)


def encode_packet(packet: Packet) -> bytes:
    """
    Encode any packet type to binary.

    Args:
        packet: Packet instance (FilePacket, MessagePacket, or custom)

    Returns:
        Binary encoded packet

    Raises:
        PacketTypeError: If packet type not recognized
    """
    # Import here to avoid circular dependency
    from .packet_codec import encode_file_packet, encode_message_packet

    if packet.packet_type == PACKET_TYPE_FILE:
        return encode_file_packet(packet)
    elif packet.packet_type == PACKET_TYPE_MESSAGE:
        return encode_message_packet(packet)
    else:
        # Check registry for custom types
        if packet.packet_type in _packet_type_registry:
            encoder_func = _packet_type_registry[packet.packet_type].encode
            if callable(encoder_func):
                return encoder_func(packet)
        raise PacketTypeError(f"Unknown packet type: {packet.packet_type}")


def decode_packet(data: bytes) -> Packet:
    """
    Decode binary data to appropriate packet type.

    Args:
        data: Raw packet bytes

    Returns:
        Decoded Packet (FilePacket, MessagePacket, or custom type)

    Raises:
        PacketDecodeError: If packet data is malformed
        PacketTypeError: If packet type not recognized
    """
    if len(data) < 1:
        raise PacketDecodeError("Packet data too short (empty)")

    # Peek at packet type (first byte)
    packet_type = data[0]

    # Import here to avoid circular dependency
    from .packet_codec import decode_file_packet, decode_message_packet

    if packet_type == PACKET_TYPE_FILE:
        return decode_file_packet(data)
    elif packet_type == PACKET_TYPE_MESSAGE:
        return decode_message_packet(data)
    else:
        # Check registry for custom types
        if packet_type in _packet_type_registry:
            decoder_func = _packet_type_registry[packet_type].decode
            if callable(decoder_func):
                return decoder_func(data)
        raise PacketTypeError(f"Unknown packet type: {packet_type}")


def get_packet_type(data: bytes) -> int:
    """
    Peek at packet type without full decode.

    Args:
        data: Raw packet bytes

    Returns:
        Packet type constant (PACKET_TYPE_FILE, PACKET_TYPE_MESSAGE, etc.)

    Raises:
        PacketDecodeError: If packet data too short
    """
    if len(data) < 1:
        raise PacketDecodeError("Packet data too short (cannot peek type)")
    return data[0]
