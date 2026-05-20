# asimov/net/packet.py
# Packet types, encoding/decoding, and packet classes

import struct
import time
import socket
from typing import Optional, Dict, Any

PACKET_TYPE_PING = 1
PACKET_TYPE_PONG = 2
PACKET_TYPE_EOS = 3

_packet_type_registry: Dict[int, type] = {}


class NetError(Exception):
    """Base exception for network errors."""

    pass


class PacketTypeError(NetError):
    """Raised when packet type is unknown."""

    pass


class PING:
    """Sentinel for PING packets."""

    pass


class PONG:
    """Sentinel for PONG packets."""

    pass


class EOS:
    """Sentinel for End-of-Stream packets."""

    pass


def register_packet_type(packet_class):
    """Register a packet class for dynamic decoding."""
    if hasattr(packet_class, "packet_type"):
        _packet_type_registry[packet_class.packet_type] = packet_class
    return packet_class


def encode_packet(packet_type: int, **kwargs) -> bytes:
    """Encode a packet with given type and fields."""
    if packet_type == PACKET_TYPE_PING:
        payload = struct.pack("!d", time.time())
        return _encode_header(PACKET_TYPE_PING, payload) + payload
    elif packet_type == PACKET_TYPE_PONG:
        orig_ts = kwargs.get("timestamp", time.time())
        payload = struct.pack("!d", orig_ts)
        return _encode_header(PACKET_TYPE_PONG, payload) + payload
    elif packet_type == PACKET_TYPE_EOS:
        payload = b""
        return _encode_header(PACKET_TYPE_EOS, payload) + payload
    else:
        raise PacketTypeError(f"Unknown packet type: {packet_type}")


def _encode_header(packet_type: int, payload: bytes) -> bytes:
    """Encode packet header with type, timestamp, and payload length."""
    timestamp = time.time()
    payload_len = len(payload)
    return struct.pack("!IdI", packet_type, timestamp, payload_len)


def decode_packet(data: bytes) -> Dict[str, Any]:
    """Decode a packet from raw bytes."""
    if len(data) < 16:
        raise NetError("Packet data too short")

    packet_type, timestamp, payload_len = struct.unpack("!IdI", data[:16])
    payload = data[16 : 16 + payload_len]

    result = {
        "packet_type": packet_type,
        "timestamp": timestamp,
        "payload": payload,
    }

    if packet_type == PACKET_TYPE_PING:
        result["packet_type"] = PING
    elif packet_type == PACKET_TYPE_PONG:
        result["packet_type"] = PONG
    elif packet_type == PACKET_TYPE_EOS:
        result["packet_type"] = EOS

    return result


class Packet:
    """
    Packet with type, payload, timestamp.
    Serialized as: [type (I)][timestamp (d)][payload length (I)][payload]
    """

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
        from .socket import recv_all

        header = recv_all(sock, 16)
        if header is None:
            return None
        ptype, timestamp, payload_len = struct.unpack("!IdI", header)
        payload = recv_all(sock, payload_len)
        if payload is None:
            return None
        return Packet(ptype, payload, timestamp)
