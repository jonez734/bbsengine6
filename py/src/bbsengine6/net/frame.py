# asimov/net/frame.py
# Frame packet types, encoding/decoding for video frame transmission

import struct
import time
from dataclasses import dataclass, field
from typing import List, Optional

from .packet import Packet

PACKET_TYPE_FRAME = 5

FRAME_PACKET_HEADER_FORMAT = "!BdIIHHHHHHHBBHB"
FRAME_PACKET_HEADER_SIZE = struct.calcsize(FRAME_PACKET_HEADER_FORMAT)


@dataclass
class FramePacket(Packet):
    """Packet for transmitting frame chunks with delta and batching support."""

    frame_id: int = 0
    block_id: int = 0
    cols: int = 0
    rows: int = 0
    block_w: int = 0
    block_h: int = 0
    block_size: int = 0
    width: int = 0
    height: int = 0
    total_blocks: int = 0
    is_delta: bool = False
    compressed: bool = False
    blocks: List[bytes] = field(default_factory=list)
    packet_type: int = field(init=False, default=PACKET_TYPE_FRAME)
    timestamp: float = field(default_factory=time.time)
    blocks_in_packet: int = 1
    block_sizes: Optional[List[int]] = None

    def __post_init__(self):
        self.packet_type = PACKET_TYPE_FRAME


def encode_frame_header(packet: FramePacket) -> bytes:
    """Encode frame packet header."""
    return struct.pack(
        FRAME_PACKET_HEADER_FORMAT,
        packet.packet_type,
        packet.timestamp,
        packet.frame_id,
        packet.block_id,
        packet.cols,
        packet.rows,
        packet.block_w,
        packet.block_h,
        packet.width,
        packet.height,
        packet.total_blocks,
        1 if packet.is_delta else 0,
        1 if packet.compressed else 0,
        packet.blocks_in_packet,
        1 if packet.block_sizes else 0,
    )


def encode_frame_packet(packet: FramePacket) -> bytes:
    """Encode frame packet with header and body."""
    header = encode_frame_header(packet)

    if packet.block_sizes:
        sizes_data = b"".join(struct.pack("!H", s) for s in packet.block_sizes)
        body = sizes_data + b"".join(packet.blocks)
    else:
        body = b"".join(packet.blocks)

    return header + body


def decode_frame_packet(data: bytes) -> FramePacket:
    """Decode frame packet from raw bytes."""
    header_size = FRAME_PACKET_HEADER_SIZE
    header = data[:header_size]
    (
        packet_type,
        timestamp,
        frame_id,
        block_id,
        cols,
        rows,
        block_w,
        block_h,
        width,
        height,
        total_blocks,
        is_delta_flag,
        compressed_flag,
        blocks_in_packet,
        has_block_sizes,
    ) = struct.unpack(FRAME_PACKET_HEADER_FORMAT, header)

    body = data[header_size:]
    blocks = []
    block_sizes = None

    if has_block_sizes and blocks_in_packet > 0:
        block_sizes = []
        sizes_size = blocks_in_packet * 2
        if len(body) >= sizes_size:
            sizes_data = body[:sizes_size]
            for i in range(blocks_in_packet):
                size = struct.unpack("!H", sizes_data[i * 2 : (i + 1) * 2])[0]
                block_sizes.append(size)

            body = body[sizes_size:]
            offset = 0
            for size in block_sizes:
                if offset + size <= len(body):
                    block = body[offset : offset + size]
                    blocks.append(block)
                    offset += size
    else:
        block_data_len = len(body) // blocks_in_packet if blocks_in_packet > 0 else 0
        offset = 0
        for _ in range(blocks_in_packet):
            if offset + block_data_len <= len(body):
                block = body[offset : offset + block_data_len]
                blocks.append(block)
                offset += block_data_len

    return FramePacket(
        frame_id=frame_id,
        block_id=block_id,
        cols=cols,
        rows=rows,
        block_w=block_w,
        block_h=block_h,
        width=width,
        height=height,
        total_blocks=total_blocks,
        is_delta=bool(is_delta_flag),
        compressed=bool(compressed_flag),
        blocks=blocks,
        timestamp=timestamp,
        blocks_in_packet=blocks_in_packet,
        block_sizes=block_sizes,
    )
