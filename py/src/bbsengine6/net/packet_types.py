# bbsengine6/net/packet_types.py
# FilePacket, MessagePacket, PingPacket, and PongPacket type definitions with validation

import struct
from dataclasses import dataclass, field

from .packet import (
    PACKET_TYPE_FILE,
    PACKET_TYPE_MESSAGE,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    BlockPacket,
    register_packet_type,
)

FILEPACKET_HEADER_FORMAT = "!BdIHQHIIBBHH"
FILEPACKET_HEADER_SIZE = struct.calcsize(FILEPACKET_HEADER_FORMAT)

MESSAGEPACKET_HEADER_FORMAT = "!BdIHHHIBH"
MESSAGEPACKET_HEADER_SIZE = struct.calcsize(MESSAGEPACKET_HEADER_FORMAT)

PINGPACKET_HEADER_FORMAT = "!Bd"
PINGPACKET_HEADER_SIZE = struct.calcsize(PINGPACKET_HEADER_FORMAT)

PONGPACKET_HEADER_FORMAT = "!Bd"
PONGPACKET_HEADER_SIZE = struct.calcsize(PONGPACKET_HEADER_FORMAT)


@register_packet_type
@dataclass
class FilePacket(BlockPacket):
    """Packet for transmitting files with block support."""

    filename: str = ""
    file_size: int = 0
    mime_type: str = "application/octet-stream"
    total_blocks: int = 0
    block_id: int = 0
    packet_type: int = field(init=False, default=PACKET_TYPE_FILE)

    def __post_init__(self) -> None:
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
class MessagePacket(BlockPacket):
    """Packet for transmitting messages (RFC 822 aligned)."""

    sender: str = ""
    subject: str = ""
    content_type: str = "text/plain"
    content: bytes = b""
    packet_type: int = field(init=False, default=PACKET_TYPE_MESSAGE)

    def __post_init__(self) -> None:
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
class PingPacket(BlockPacket):
    """Packet for keep-alive PING requests."""

    packet_type: int = field(init=False, default=PACKET_TYPE_PING)


@register_packet_type
@dataclass
class PongPacket(BlockPacket):
    """Packet for keep-alive PONG responses."""

    packet_type: int = field(init=False, default=PACKET_TYPE_PONG)
