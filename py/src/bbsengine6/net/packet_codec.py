# bbsengine6/net/packet_codec.py
# Encode/decode functions for FilePacket and MessagePacket with compression and checksums

import hashlib
import hmac
import struct
import zlib
from typing import List

from .packet import (
    CHECKSUM_HEX_LEN,
    MAX_PAYLOAD_SIZE,
    PacketChecksumError,
    PacketDecodeError,
)
from .packet_types import (
    FILEPACKET_HEADER_FORMAT,
    FILEPACKET_HEADER_SIZE,
    MESSAGEPACKET_HEADER_FORMAT,
    MESSAGEPACKET_HEADER_SIZE,
    FilePacket,
    MessagePacket,
)


# Compression utilities


def compress_blocks(blocks: List[bytes]) -> List[bytes]:
    """
    Compress blocks using zlib.

    Args:
        blocks: List of uncompressed blocks

    Returns:
        List of compressed blocks

    Raises:
        ValueError: If compression fails
    """
    try:
        return [zlib.compress(block, level=6) for block in blocks]
    except zlib.error as e:
        raise ValueError(f"Compression failed: {e}")


def decompress_blocks(blocks: List[bytes]) -> List[bytes]:
    """
    Decompress blocks using zlib.

    Args:
        blocks: List of compressed blocks

    Returns:
        List of decompressed blocks

    Raises:
        ValueError: If decompression fails
    """
    try:
        return [zlib.decompress(block) for block in blocks]
    except zlib.error as e:
        raise ValueError(f"Decompression failed: {e}")


# Checksum utilities


def compute_checksum(data: bytes) -> str:
    """
    Compute SHA256 checksum of data.

    Args:
        data: Bytes to hash

    Returns:
        SHA256 hash as 64-character hex string
    """
    return hashlib.sha256(data).hexdigest()


def verify_checksum(data: bytes, checksum_hex: str) -> bool:
    """
    Verify SHA256 checksum using constant-time comparison.

    Args:
        data: Bytes to verify
        checksum_hex: Expected SHA256 hex string (64 chars)

    Returns:
        True if checksum matches, False otherwise
    """
    expected = compute_checksum(data)
    # Use hmac.compare_digest for constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(expected, checksum_hex)


# Filename validation


def validate_filename(filename: str) -> str:
    """
    Validate filename is safe (no path traversal, ASCII-only).

    Args:
        filename: Filename to validate

    Returns:
        Validated filename

    Raises:
        ValueError: If filename invalid
    """
    if not filename:
        raise ValueError("filename cannot be empty")

    # Validate ASCII
    try:
        filename.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("filename must be ASCII")

    # Validate length
    if len(filename) > 256:
        raise ValueError(f"filename too long: {len(filename)} > 256 bytes")

    # Check for path traversal characters
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("filename contains path traversal characters")

    # Check for null bytes
    if "\x00" in filename:
        raise ValueError("filename contains null bytes")

    return filename


# FilePacket encoding/decoding


def encode_file_packet(packet: FilePacket) -> bytes:
    """
    Encode FilePacket to binary.

    Args:
        packet: FilePacket to encode

    Returns:
        Binary encoded packet

    Raises:
        ValueError: If packet invalid or encoding fails
        PacketDecodeError: If payload too large
    """
    # Validate filename
    validate_filename(packet.filename)

    # Encode strings to ASCII bytes
    filename_bytes = packet.filename.encode("ascii")
    mime_type_bytes = packet.mime_type.encode("ascii")

    # Validate sizes before packing
    if len(filename_bytes) > 65535:
        raise ValueError("filename too long")
    if len(mime_type_bytes) > 65535:
        raise ValueError("mime_type too long")

    # Prepare blocks
    blocks_to_use = packet.blocks
    if packet.compressed and blocks_to_use:
        blocks_to_use = compress_blocks(blocks_to_use)

    # Calculate block sizes
    block_sizes = [len(b) for b in blocks_to_use]
    has_block_sizes = 1 if block_sizes else 0

    # Compute payload checksum (before packing header)
    payload_data = b"".join(blocks_to_use)
    checksum_hex = compute_checksum(payload_data)

    # Pack header
    header = struct.pack(
        FILEPACKET_HEADER_FORMAT,
        packet.packet_type,
        packet.timestamp,
        packet.packet_id,
        len(filename_bytes),
        packet.file_size,
        len(mime_type_bytes),
        packet.total_blocks,
        packet.block_id,
        1 if packet.compressed else 0,
        has_block_sizes,
        len(block_sizes),
        CHECKSUM_HEX_LEN,
    )

    # Build packet: header + filename + mime_type + block_sizes + blocks + checksum
    packet_data = header + filename_bytes + mime_type_bytes

    # Add block sizes if present
    if block_sizes:
        for size in block_sizes:
            packet_data += struct.pack("!H", size)

    # Add blocks and checksum
    packet_data += payload_data + checksum_hex.encode("ascii")

    # Validate total payload size (excluding header)
    payload_size = (
        len(filename_bytes)
        + len(mime_type_bytes)
        + (len(block_sizes) * 2 if block_sizes else 0)
        + len(payload_data)
        + CHECKSUM_HEX_LEN
    )
    if payload_size >= MAX_PAYLOAD_SIZE:
        raise PacketDecodeError(
            f"Payload too large: {payload_size} >= {MAX_PAYLOAD_SIZE}"
        )

    return packet_data


def decode_file_packet(data: bytes) -> FilePacket:
    """
    Decode binary to FilePacket.

    Args:
        data: Raw packet bytes

    Returns:
        Decoded FilePacket

    Raises:
        PacketDecodeError: If packet malformed
        PacketChecksumError: If checksum mismatch
    """
    # Validate minimum size
    if len(data) < FILEPACKET_HEADER_SIZE:
        raise PacketDecodeError(
            f"FilePacket header too short: {len(data)} < {FILEPACKET_HEADER_SIZE}"
        )

    # Unpack header
    try:
        header = data[:FILEPACKET_HEADER_SIZE]
        (
            packet_type,
            timestamp,
            packet_id,
            filename_len,
            file_size,
            mime_type_len,
            total_blocks,
            block_id,
            compressed_flag,
            has_block_sizes,
            blocks_in_packet,
            checksum_len,
        ) = struct.unpack(FILEPACKET_HEADER_FORMAT, header)
    except struct.error as e:
        raise PacketDecodeError(f"Failed to unpack header: {e}")

    # Validate header fields
    if filename_len < 1 or filename_len > 65535:
        raise PacketDecodeError(f"Invalid filename_len: {filename_len}")
    if mime_type_len < 1 or mime_type_len > 65535:
        raise PacketDecodeError(f"Invalid mime_type_len: {mime_type_len}")
    if total_blocks < 1 or total_blocks > 4294967295:
        raise PacketDecodeError(f"Invalid total_blocks: {total_blocks}")
    if block_id >= total_blocks:
        raise PacketDecodeError(
            f"Invalid block_id: {block_id} >= total_blocks {total_blocks}"
        )
    if checksum_len != CHECKSUM_HEX_LEN:
        raise PacketDecodeError(
            f"Invalid checksum_len: {checksum_len} != {CHECKSUM_HEX_LEN}"
        )

    # Extract strings
    offset = FILEPACKET_HEADER_SIZE
    if offset + filename_len > len(data):
        raise PacketDecodeError("Packet truncated: missing filename")
    filename = data[offset : offset + filename_len].decode("ascii", errors="replace")
    offset += filename_len

    if offset + mime_type_len > len(data):
        raise PacketDecodeError("Packet truncated: missing mime_type")
    mime_type = data[offset : offset + mime_type_len].decode("ascii", errors="replace")
    offset += mime_type_len

    # Extract block sizes if present
    block_sizes = None
    if has_block_sizes and blocks_in_packet > 0:
        block_sizes = []
        sizes_size = blocks_in_packet * 2
        if offset + sizes_size > len(data):
            raise PacketDecodeError("Packet truncated: missing block_sizes")
        for i in range(blocks_in_packet):
            size = struct.unpack("!H", data[offset : offset + 2])[0]
            block_sizes.append(size)
            offset += 2

    # Extract blocks
    blocks = []
    if blocks_in_packet > 0:
        if block_sizes:
            for size in block_sizes:
                if offset + size > len(data) - CHECKSUM_HEX_LEN:
                    raise PacketDecodeError("Packet truncated: missing block data")
                blocks.append(data[offset : offset + size])
                offset += size
        else:
            # Single block, calculate size from remaining data (excluding checksum)
            block_data_len = len(data) - offset - CHECKSUM_HEX_LEN
            if block_data_len < 0:
                raise PacketDecodeError("Packet truncated: missing checksum")
            if block_data_len > 0:
                blocks.append(data[offset : offset + block_data_len])
                offset += block_data_len

    # Extract checksum
    if offset + CHECKSUM_HEX_LEN > len(data):
        raise PacketDecodeError("Packet truncated: missing checksum")
    checksum_hex = data[offset : offset + CHECKSUM_HEX_LEN].decode(
        "ascii", errors="replace"
    )

    # Verify checksum
    payload_data = b"".join(blocks)
    if not verify_checksum(payload_data, checksum_hex):
        raise PacketChecksumError("FilePacket checksum mismatch")

    # Decompress if needed
    if compressed_flag and blocks:
        blocks = decompress_blocks(blocks)

    # Create and return packet
    return FilePacket(
        filename=filename,
        file_size=file_size,
        mime_type=mime_type,
        total_blocks=total_blocks,
        block_id=block_id,
        blocks=blocks,
        block_sizes=block_sizes,
        blocks_in_packet=blocks_in_packet,
        compressed=bool(compressed_flag),
        timestamp=timestamp,
        packet_id=packet_id,
        checksum=checksum_hex,
    )


# MessagePacket encoding/decoding


def encode_message_packet(packet: MessagePacket) -> bytes:
    """
    Encode MessagePacket to binary.

    Args:
        packet: MessagePacket to encode

    Returns:
        Binary encoded packet

    Raises:
        ValueError: If packet invalid or encoding fails
        PacketDecodeError: If payload too large
    """
    # Encode strings to ASCII bytes
    sender_bytes = packet.sender.encode("ascii")
    subject_bytes = packet.subject.encode("ascii")
    content_type_bytes = packet.content_type.encode("ascii")

    # Validate sizes
    if len(sender_bytes) > 65535:
        raise ValueError("sender too long")
    if len(subject_bytes) > 65535:
        raise ValueError("subject too long")
    if len(content_type_bytes) > 65535:
        raise ValueError("content_type too long")

    # Prepare content
    content_to_use = packet.content
    if packet.compressed and content_to_use:
        content_to_use = zlib.compress(content_to_use, level=6)

    # Compute checksum (before packing header)
    checksum_hex = compute_checksum(content_to_use)

    # Pack header
    header = struct.pack(
        MESSAGEPACKET_HEADER_FORMAT,
        packet.packet_type,
        packet.timestamp,
        packet.packet_id,
        len(sender_bytes),
        len(subject_bytes),
        len(content_type_bytes),
        len(content_to_use),
        1 if packet.compressed else 0,
        CHECKSUM_HEX_LEN,
    )

    # Build packet
    packet_data = (
        header
        + sender_bytes
        + subject_bytes
        + content_type_bytes
        + content_to_use
        + checksum_hex.encode("ascii")
    )

    # Validate total payload size
    payload_size = (
        len(sender_bytes)
        + len(subject_bytes)
        + len(content_type_bytes)
        + len(content_to_use)
        + CHECKSUM_HEX_LEN
    )
    if payload_size >= MAX_PAYLOAD_SIZE:
        raise PacketDecodeError(
            f"Payload too large: {payload_size} >= {MAX_PAYLOAD_SIZE}"
        )

    return packet_data


def decode_message_packet(data: bytes) -> MessagePacket:
    """
    Decode binary to MessagePacket.

    Args:
        data: Raw packet bytes

    Returns:
        Decoded MessagePacket

    Raises:
        PacketDecodeError: If packet malformed
        PacketChecksumError: If checksum mismatch
    """
    # Validate minimum size
    if len(data) < MESSAGEPACKET_HEADER_SIZE:
        raise PacketDecodeError(
            f"MessagePacket header too short: {len(data)} < {MESSAGEPACKET_HEADER_SIZE}"
        )

    # Unpack header
    try:
        header = data[:MESSAGEPACKET_HEADER_SIZE]
        (
            packet_type,
            timestamp,
            packet_id,
            sender_len,
            subject_len,
            content_type_len,
            content_len,
            compressed_flag,
            checksum_len,
        ) = struct.unpack(MESSAGEPACKET_HEADER_FORMAT, header)
    except struct.error as e:
        raise PacketDecodeError(f"Failed to unpack header: {e}")

    # Validate header fields
    if sender_len < 1 or sender_len > 65535:
        raise PacketDecodeError(f"Invalid sender_len: {sender_len}")
    if subject_len < 0 or subject_len > 65535:
        raise PacketDecodeError(f"Invalid subject_len: {subject_len}")
    if content_type_len < 1 or content_type_len > 65535:
        raise PacketDecodeError(f"Invalid content_type_len: {content_type_len}")
    if content_len > 4294967295:
        raise PacketDecodeError(f"Invalid content_len: {content_len}")
    if checksum_len != CHECKSUM_HEX_LEN:
        raise PacketDecodeError(
            f"Invalid checksum_len: {checksum_len} != {CHECKSUM_HEX_LEN}"
        )

    # Extract strings and content
    offset = MESSAGEPACKET_HEADER_SIZE
    if offset + sender_len > len(data):
        raise PacketDecodeError("Packet truncated: missing sender")
    sender = data[offset : offset + sender_len].decode("ascii", errors="replace")
    offset += sender_len

    if offset + subject_len > len(data):
        raise PacketDecodeError("Packet truncated: missing subject")
    subject = data[offset : offset + subject_len].decode("ascii", errors="replace")
    offset += subject_len

    if offset + content_type_len > len(data):
        raise PacketDecodeError("Packet truncated: missing content_type")
    content_type = data[offset : offset + content_type_len].decode(
        "ascii", errors="replace"
    )
    offset += content_type_len

    if offset + content_len > len(data) - CHECKSUM_HEX_LEN:
        raise PacketDecodeError("Packet truncated: missing content")
    content = data[offset : offset + content_len]
    offset += content_len

    # Extract checksum
    if offset + CHECKSUM_HEX_LEN > len(data):
        raise PacketDecodeError("Packet truncated: missing checksum")
    checksum_hex = data[offset : offset + CHECKSUM_HEX_LEN].decode(
        "ascii", errors="replace"
    )

    # Verify checksum
    if not verify_checksum(content, checksum_hex):
        raise PacketChecksumError("MessagePacket checksum mismatch")

    # Decompress if needed
    if compressed_flag and content:
        content = zlib.decompress(content)

    # Create and return packet
    return MessagePacket(
        sender=sender,
        subject=subject,
        content_type=content_type,
        content=content,
        timestamp=timestamp,
        packet_id=packet_id,
        blocks=[content],  # Store content as single block for consistency
        compressed=bool(compressed_flag),
        checksum=checksum_hex,
    )


# PingPacket and PongPacket encoding/decoding


def encode_ping_packet(packet) -> bytes:
    """
    Encode PingPacket to binary.

    PING packets are minimal - just the timestamp in a small header.

    Args:
        packet: PingPacket to encode

    Returns:
        Binary encoded packet (9 bytes: 1 byte type + 8 bytes timestamp)
    """
    from .packet import PACKET_TYPE_PING

    header = struct.pack("!Bd", PACKET_TYPE_PING, packet.timestamp)
    return header


def decode_ping_packet(data: bytes):
    """
    Decode binary to PingPacket.

    Args:
        data: Raw packet bytes

    Returns:
        Decoded PingPacket

    Raises:
        PacketDecodeError: If packet malformed
    """
    from .packet import PACKET_TYPE_PING
    from .packet_types import PingPacket

    if len(data) < 9:
        raise PacketDecodeError(f"PING packet too short: {len(data)} < 9")

    try:
        packet_type, timestamp = struct.unpack("!Bd", data[:9])
    except struct.error as e:
        raise PacketDecodeError(f"Failed to unpack PING header: {e}")

    if packet_type != PACKET_TYPE_PING:
        raise PacketDecodeError(f"Invalid PING packet type: {packet_type}")

    return PingPacket(timestamp=timestamp, packet_id=0)


def encode_pong_packet(packet) -> bytes:
    """
    Encode PongPacket to binary.

    PONG packets are minimal - just the timestamp in a small header.

    Args:
        packet: PongPacket to encode

    Returns:
        Binary encoded packet (9 bytes: 1 byte type + 8 bytes timestamp)
    """
    from .packet import PACKET_TYPE_PONG

    header = struct.pack("!Bd", PACKET_TYPE_PONG, packet.timestamp)
    return header


def decode_pong_packet(data: bytes):
    """
    Decode binary to PongPacket.

    Args:
        data: Raw packet bytes

    Returns:
        Decoded PongPacket

    Raises:
        PacketDecodeError: If packet malformed
    """
    from .packet import PACKET_TYPE_PONG
    from .packet_types import PongPacket

    if len(data) < 9:
        raise PacketDecodeError(f"PONG packet too short: {len(data)} < 9")

    try:
        packet_type, timestamp = struct.unpack("!Bd", data[:9])
    except struct.error as e:
        raise PacketDecodeError(f"Failed to unpack PONG header: {e}")

    if packet_type != PACKET_TYPE_PONG:
        raise PacketDecodeError(f"Invalid PONG packet type: {packet_type}")

    return PongPacket(timestamp=timestamp, packet_id=0)
