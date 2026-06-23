# bbsengine6/net/packet.py
# Unified packet system for Files and Messages with block support, compression, and checksums

import struct
import time
import socket
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .crypto import CryptoHash

# Packet type constants
PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_FILE = 10
PACKET_TYPE_MESSAGE = 11

# TODO: Add PACKET_TYPE_SETBOTTOMBAR = 12 for server-to-client UI updates
# This will allow the server to update the client's bottom bar (e.g., from casino module).
# When implemented:
# - Add SetBottomBarPacket class in packet_types.py with @register_packet_type decorator
# - Add encode/decode functions in packet_codec.py
# - Client should check sys.stdout.isatty() to decide whether to call io.screen.setbottombar()
#   or print the message for automated testing

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
    """Register a packet class for dynamic decoding."""
    if hasattr(packet_class, "packet_type"):
        _packet_type_registry[packet_class.packet_type] = packet_class
    return packet_class


# Test-compatible Packet class (asimov-style API for backward compat with tests)
class Packet:
    """Packet with type, payload, timestamp. Serialized as: [type (I)][timestamp (d)][payload length (I)][payload]."""

    def __init__(self, ptype: int, payload: bytes = b"", timestamp: float = 0.0):
        self.ptype = ptype
        self.payload = payload
        self.timestamp = timestamp if timestamp != 0.0 else time.time()

    def encode(self) -> bytes:
        payload_len = len(self.payload)
        header = struct.pack("!IdI", self.ptype, self.timestamp, payload_len)
        return header + self.payload

    @staticmethod
    def decode(data: bytes) -> "Packet":
        if len(data) < 16:
            raise ValueError("Packet data too short")
        ptype, timestamp, payload_len = struct.unpack("!IdI", data[:16])
        payload = data[16 : 16 + payload_len]
        return Packet(ptype, payload, timestamp)

    @staticmethod
    def recv(sock: socket.socket) -> Optional["Packet"]:
        header = _recv_all(sock, 16)
        if header is None:
            return None
        ptype, timestamp, payload_len = struct.unpack("!IdI", header)
        payload = _recv_all(sock, payload_len)
        if payload is None:
            return None
        return Packet(ptype, payload, timestamp)


def _recv_all(sock: socket.socket, length: int) -> Optional[bytes]:
    """Receive exactly `length` bytes from a socket, or None if closed."""
    data = bytearray()
    while len(data) < length:
        try:
            chunk = sock.recv(length - len(data))
        except socket.error:
            return None
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


@dataclass
class BlockPacket:
    """Base packet class with common fields.

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


def encode_packet(packet: BlockPacket, crypto: Optional["CryptoHash"] = None) -> bytes:
    """Encode any packet type to binary."""
    from .packet_codec import (
        encode_file_packet,
        encode_message_packet,
        encode_ping_packet,
        encode_pong_packet,
    )

    if packet.packet_type == PACKET_TYPE_PING:
        return encode_ping_packet(packet)
    elif packet.packet_type == PACKET_TYPE_PONG:
        return encode_pong_packet(packet)
    elif packet.packet_type == PACKET_TYPE_FILE:
        return encode_file_packet(packet, crypto=crypto)
    elif packet.packet_type == PACKET_TYPE_MESSAGE:
        return encode_message_packet(packet, crypto=crypto)
    else:
        if packet.packet_type in _packet_type_registry:
            encoder_func = _packet_type_registry[packet.packet_type].encode
            if callable(encoder_func):
                return encoder_func(packet)
        raise PacketTypeError(f"Unknown packet type: {packet.packet_type}")


def decode_packet(data: bytes, crypto: Optional["CryptoHash"] = None) -> BlockPacket:
    """Decode binary data to appropriate packet type."""
    if len(data) < 1:
        raise PacketDecodeError("Packet data too short (empty)")

    packet_type = data[0]

    from .packet_codec import (
        decode_file_packet,
        decode_message_packet,
        decode_ping_packet,
        decode_pong_packet,
    )

    if packet_type == PACKET_TYPE_PING:
        return decode_ping_packet(data)
    elif packet_type == PACKET_TYPE_PONG:
        return decode_pong_packet(data)
    elif packet_type == PACKET_TYPE_FILE:
        return decode_file_packet(data, crypto=crypto)
    elif packet_type == PACKET_TYPE_MESSAGE:
        return decode_message_packet(data, crypto=crypto)
    else:
        if packet_type in _packet_type_registry:
            decoder_func = _packet_type_registry[packet_type].decode
            if callable(decoder_func):
                return decoder_func(data)
        raise PacketTypeError(f"Unknown packet type: {packet_type}")


def get_packet_type(data: bytes) -> int:
    """Peek at packet type without full decode."""
    if len(data) < 1:
        raise PacketDecodeError("Packet data too short (cannot peek type)")
    return data[0]
