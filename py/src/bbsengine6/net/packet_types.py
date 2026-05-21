# bbsengine6/net/packet_types.py
# FilePacket, MessagePacket, PingPacket, and PongPacket type definitions with validation

import struct
from dataclasses import dataclass, field

from .packet import (
    PACKET_TYPE_FILE,
    PACKET_TYPE_MESSAGE,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    Packet,
    register_packet_type,
)

# FilePacket header format and size
FILEPACKET_HEADER_FORMAT = "!BdIHQHIIBBHH"
FILEPACKET_HEADER_SIZE = struct.calcsize(FILEPACKET_HEADER_FORMAT)

# MessagePacket header format and size
MESSAGEPACKET_HEADER_FORMAT = "!BdIHHHIBH"
MESSAGEPACKET_HEADER_SIZE = struct.calcsize(MESSAGEPACKET_HEADER_FORMAT)

# PingPacket header format and size
PINGPACKET_HEADER_FORMAT = "!Bd"
PINGPACKET_HEADER_SIZE = struct.calcsize(PINGPACKET_HEADER_FORMAT)

# PongPacket header format and size
PONGPACKET_HEADER_FORMAT = "!Bd"
PONGPACKET_HEADER_SIZE = struct.calcsize(PONGPACKET_HEADER_FORMAT)


@register_packet_type
@dataclass
class FilePacket(Packet):
    """
    Packet for transmitting files with block support.

    Files larger than 1MB are split across multiple FilePackets,
    each with the same filename/file_size but different block_id.

    Attributes:
        filename: Name of file (ASCII, 1-256 bytes)
        file_size: Total file size in bytes
        mime_type: MIME type (ASCII, 1-256 bytes)
        total_blocks: Total number of blocks this file is split into
        block_id: Which block this packet contains (0-indexed)
        blocks: List with single block data (due to < 1MB payload limit)
    """

    filename: str = ""
    file_size: int = 0
    mime_type: str = "application/octet-stream"
    total_blocks: int = 0
    block_id: int = 0
    packet_type: int = field(init=False, default=PACKET_TYPE_FILE)

    def __post_init__(self) -> None:
        """Validate FilePacket fields."""
        if not self.filename:
            raise ValueError("filename cannot be empty")
        if len(self.filename) > 256:
            raise ValueError(f"filename too long: {len(self.filename)} > 256 bytes")
        try:
            self.filename.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("filename must be ASCII")

        if self.file_size <= 0:
            raise ValueError(f"file_size must be > 0, got {self.file_size}")

        if not self.mime_type:
            raise ValueError("mime_type cannot be empty")
        if len(self.mime_type) > 256:
            raise ValueError(f"mime_type too long: {len(self.mime_type)} > 256 bytes")
        try:
            self.mime_type.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("mime_type must be ASCII")

        if self.total_blocks <= 0:
            raise ValueError(f"total_blocks must be > 0, got {self.total_blocks}")
        if self.block_id >= self.total_blocks:
            raise ValueError(
                f"block_id {self.block_id} >= total_blocks {self.total_blocks}"
            )


@register_packet_type
@dataclass
class MessagePacket(Packet):
    """
    Packet for transmitting messages (RFC 822 aligned).

    Represents an email-like message with sender, subject, content type,
    and content. Maps directly to RFC 822 email headers:
    - From: → sender
    - Subject: → subject
    - Content-Type: → content_type
    - Date: → timestamp (implicit)

    Attributes:
        sender: Message sender (ASCII, 1-256 bytes)
        subject: Message subject (ASCII, 0-256 bytes, can be empty)
        content_type: MIME type of content (ASCII, 1-256 bytes)
        content: Message body (raw bytes, < 1 MB)
    """

    sender: str = ""
    subject: str = ""
    content_type: str = "text/plain"
    content: bytes = b""
    packet_type: int = field(init=False, default=PACKET_TYPE_MESSAGE)

    def __post_init__(self) -> None:
        """Validate MessagePacket fields."""
        if not self.sender:
            raise ValueError("sender cannot be empty")
        if len(self.sender) > 256:
            raise ValueError(f"sender too long: {len(self.sender)} > 256 bytes")
        try:
            self.sender.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("sender must be ASCII")

        if len(self.subject) > 256:
            raise ValueError(f"subject too long: {len(self.subject)} > 256 bytes")
        try:
            self.subject.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("subject must be ASCII")

        if not self.content_type:
            raise ValueError("content_type cannot be empty")
        if len(self.content_type) > 256:
            raise ValueError(
                f"content_type too long: {len(self.content_type)} > 256 bytes"
            )
        try:
            self.content_type.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("content_type must be ASCII")

        if not isinstance(self.content, bytes):
            raise ValueError("content must be bytes")
        if len(self.content) > 1_048_575:
            raise ValueError(f"content too large: {len(self.content)} > 1048575 bytes")


@register_packet_type
@dataclass
class PingPacket(Packet):
    """
    Packet for keep-alive PING requests.

    Used to verify connection health and detect stale connections.
    Server should respond with PongPacket containing the same timestamp
    to allow sender to calculate round-trip latency.

    This is a minimal packet type for transport-level health checking.
    """

    packet_type: int = field(init=False, default=PACKET_TYPE_PING)

    def __post_init__(self) -> None:
        """Validate PingPacket fields."""
        # PING packets are minimal - just timestamp is enough
        pass


@register_packet_type
@dataclass
class PongPacket(Packet):
    """
    Packet for keep-alive PONG responses.

    Response to a PingPacket. Contains the original PING timestamp
    to allow sender to calculate round-trip latency.

    This is a minimal packet type for transport-level health checking.
    """

    packet_type: int = field(init=False, default=PACKET_TYPE_PONG)

    def __post_init__(self) -> None:
        """Validate PongPacket fields."""
        # PONG packets are minimal - just timestamp is enough
        pass
