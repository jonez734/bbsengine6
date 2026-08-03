"""
Regression tests for Phase 2 net/packet.py hardening.

Covers:
- Packet.decode rejects payloads larger than MAX_PAYLOAD_SIZE.
- Packet.decode rejects truncated payloads.
- Packet.decode rejects negative payload lengths.
- Packet.decode rejects empty data.
- Packet.decode accepts small valid packets round-trip.
"""

import struct

import pytest

from bbsengine6.net.packet import (
    MAX_PAYLOAD_SIZE,
    Packet,
)


pytestmark = pytest.mark.unit


def _encode_header(ptype: int, timestamp: float, payload_len: int) -> bytes:
    return struct.pack("!IdI", ptype, timestamp, payload_len)


def test_packet_decode_rejects_oversized_payload():
    """Packet.decode() must reject payload_len > MAX_PAYLOAD_SIZE."""
    header = _encode_header(10, 1.0, MAX_PAYLOAD_SIZE + 1)
    with pytest.raises(ValueError, match="payload length"):
        Packet.decode(header)


def test_packet_decode_accepts_payload_at_max():
    """payload_len == MAX_PAYLOAD_SIZE should be accepted (boundary)."""
    payload_len = MAX_PAYLOAD_SIZE
    header = _encode_header(10, 1.0, payload_len)
    # Provide exactly the right number of bytes (header + payload).
    data = header + b"\x00" * payload_len
    pkt = Packet.decode(data)
    assert pkt.ptype == 10
    assert len(pkt.payload) == payload_len


def test_packet_decode_rejects_truncated_payload():
    """If the buffer is shorter than header claims, decode must raise."""
    header = _encode_header(10, 1.0, 100)
    data = header + b"x" * 50  # only 50 of the claimed 100 bytes
    with pytest.raises(ValueError, match="truncated"):
        Packet.decode(data)


def test_packet_decode_rejects_negative_payload_length():
    """A signed-int payload_len (-1) round-trips on the wire as the
    unsigned int 0xFFFFFFFF (4_294_967_295). This is malformed because it
    exceeds MAX_PAYLOAD_SIZE; decode must raise rather than trying to
    allocate that much memory.
    """
    # Encode the length field as a SIGNED int (!i) so -1 round-trips on
    # the wire; the production code's !I unsigned unpack then sees the
    # bit pattern as 0xFFFFFFFF, which is a hostile / malformed packet.
    header = struct.pack("!Idi", 10, 1.0, -1)
    with pytest.raises(ValueError, match="exceeds"):
        Packet.decode(header)


def test_packet_decode_rejects_too_short_header():
    """Packet.decode(<16 bytes) must raise ValueError."""
    with pytest.raises(ValueError, match="too short"):
        Packet.decode(b"\x00" * 8)
    with pytest.raises(ValueError, match="too short"):
        Packet.decode(b"")


def test_packet_encode_decode_round_trip():
    """A small valid packet must encode and decode losslessly."""
    p = Packet(ptype=10, payload=b"hello world", timestamp=12345.678)
    encoded = p.encode()
    decoded = Packet.decode(encoded)
    assert decoded.ptype == 10
    assert decoded.payload == b"hello world"
    assert abs(decoded.timestamp - 12345.678) < 1e-9


def test_packet_decode_returns_packet_with_correct_ptype():
    """Multiple packet types round-trip cleanly."""
    for ptype in (1, 2, 10, 11):
        p = Packet(ptype=ptype, payload=b"x", timestamp=1.0)
        decoded = Packet.decode(p.encode())
        assert decoded.ptype == ptype


def test_packet_constants_consistent():
    """Sanity check: MAX_PAYLOAD_SIZE should be > 0 and == MAX_BLOCK_SIZE."""
    from bbsengine6.net.packet import MAX_BLOCK_SIZE

    assert MAX_PAYLOAD_SIZE > 0
    assert MAX_PAYLOAD_SIZE == MAX_BLOCK_SIZE
