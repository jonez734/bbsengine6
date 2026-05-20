# bbsengine6/net/udp.py
# UDP sender/receiver classes with frame transmission support (no numpy)

import logging
import socket
import struct
import time
import zlib
import math
from typing import Optional, Callable, Any, Union, Dict
from collections import defaultdict

from .packet import (
    encode_packet,
    decode_packet,
    PACKET_TYPE_PING,
    PACKET_TYPE_PONG,
    PACKET_TYPE_EOS,
    PING,
    PONG,
    EOS,
)
from .frame import (
    PACKET_TYPE_FRAME,
    FramePacket,
    encode_frame_packet,
    decode_frame_packet,
    FRAME_PACKET_HEADER_SIZE,
)
from .frame_address import FrameAddress, FrameAddressParser, ParseResult
from .conf import BUFFER_SIZE


UDP_MAX_PAYLOAD = 65507 - 28 - FRAME_PACKET_HEADER_SIZE


def _calc_optimal_blocks_per_packet(block_w: int, block_h: int, compress: bool) -> int:
    """Calculate max blocks that fit in UDP packet."""
    block_size = block_w * block_h * 3
    if compress:
        block_size = max(block_size // 10, 100)
    return max(1, UDP_MAX_PAYLOAD // block_size)


def _detect_delta(frame, prev_frame) -> bool:
    """
    Detect if frame differs from previous frame.
    Simple byte-level comparison (no numpy).
    """
    if prev_frame is None:
        return False
    if not isinstance(frame, bytes) or not isinstance(prev_frame, bytes):
        return True
    return frame != prev_frame


class UDPSender:
    def __init__(
        self,
        host_or_dsn: Optional[Union[str, FrameAddress]] = None,
        port: Optional[int] = None,
        *,
        dsn: Optional[str] = None,
        address: Optional[FrameAddress] = None,
        bind_port: int = 0,
        blocking: bool = False,
    ):
        """
        UDP Sender with flexible constructor.
        
        Old API: UDPSender("example.com", 4200)
        New API: UDPSender(dsn="udp://example.com:4200/")
        """
        self.addr = None
        self.blocking = blocking
        self.sock: Optional[socket.socket] = None
        self.prev_frame = None
        self.error: Optional[ParseResult] = None
        self.address: Optional[FrameAddress] = None
        
        # Validate and normalize arguments
        result = self._validate_and_normalize_args(host_or_dsn, port, dsn, address)
        if not result.success:
            self.error = result
            return
        
        self.address = result.value
        self.addr = (self.address.host, self.address.port)
        
        # Setup socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        if bind_port > 0:
            self.sock.bind(("0.0.0.0", bind_port))
        else:
            self.sock.bind(("0.0.0.0", 0))
        
        if not blocking:
            self.sock.setblocking(False)
    
    @staticmethod
    def _validate_and_normalize_args(
        host_or_dsn: Optional[Union[str, FrameAddress]],
        port: Optional[int],
        dsn: Optional[str],
        address: Optional[FrameAddress],
    ) -> ParseResult:
        """Validate and convert arguments to FrameAddress."""
        
        arg_count = sum([
            host_or_dsn is not None,
            port is not None,
            dsn is not None,
            address is not None,
        ])
        
        if arg_count == 0:
            return ParseResult(False, error="No connection parameters provided", code="NO_ARGS")
        
        if address is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix address object with other args", code="AMBIGUOUS_ARGS")
            return address.validate()
        
        if dsn is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix dsn with other args", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(dsn)
        
        if isinstance(host_or_dsn, str) and host_or_dsn.startswith(("tcp://", "udp://", "unix://", "ws://", "wss://")):
            if port is not None:
                return ParseResult(False, error="Cannot specify port with DSN string", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(host_or_dsn)
        
        if isinstance(host_or_dsn, str) and port is not None:
            from .frame_address import FrameScheme
            address = FrameAddress(
                scheme=FrameScheme.UDP,
                host=host_or_dsn,
                port=port,
                socket_path=None,
                user=None,
                password=None,
                path="/",
            )
            return address.validate()
        
        if isinstance(host_or_dsn, str) and port is None:
            return ParseResult(False, error="Port required when host provided", code="MISSING_PORT")
        
        return ParseResult(False, error="Invalid arguments", code="INVALID_ARGS")
    
    def send_frame(
        self,
        frame: bytes,
        frame_id: int,
        prev_frame: Optional[bytes] = None,
        cols: int = 0,
        rows: int = 0,
        compress: bool = False,
        full_frame: bool = False,
        auto_batch: bool = True,
        is_delta: Optional[bool] = None,
    ) -> Optional[ParseResult]:
        """Send frame. Returns error if not successful."""
        if self.error:
            return self.error
        
        if not self.sock:
            return ParseResult(False, error="Socket not initialized", code="NO_SOCKET")
        
        try:
            # Estimate frame dimensions from bytes
            if isinstance(frame, bytes):
                frame_size = len(frame)
                if frame_size == 6220800:
                    width, height = 1920, 1080
                elif frame_size == 921600:
                    width, height = 640, 480
                elif frame_size == 230400:
                    width, height = 320, 240
                else:
                    pixels = frame_size // 3
                    width = int(math.sqrt(pixels))
                    height = pixels // width
            else:
                return ParseResult(False, error="Frame must be bytes", code="INVALID_FRAME")
            
            # Determine delta mode
            if is_delta is None:
                is_delta = not full_frame and prev_frame is not None and _detect_delta(frame, prev_frame)
            
            # Calculate grid
            if cols <= 0 or rows <= 0:
                max_block_size = 64
                gcd_val = math.gcd(width, height)
                block_size = min(max_block_size, gcd_val if gcd_val > 0 else 64)
                if block_size < 8:
                    block_size = 8
                cols = (width + block_size - 1) // block_size
                rows = (height + block_size - 1) // block_size
            
            block_w = width // cols
            block_h = height // rows
            total_blocks = cols * rows
            
            blocks_per_packet = 1
            if auto_batch:
                blocks_per_packet = _calc_optimal_blocks_per_packet(block_w, block_h, compress)
            
            # Build blocks
            block_ids = list(range(total_blocks))
            
            # Send blocks in batches
            for i in range(0, len(block_ids), blocks_per_packet):
                batch_ids = block_ids[i : i + blocks_per_packet]
                blocks = []
                
                for block_id in batch_ids:
                    row = block_id // cols
                    col = block_id % cols
                    x0 = col * block_w
                    y0 = row * block_h
                    x1 = min(x0 + block_w, width)
                    y1 = min(y0 + block_h, height)
                    
                    block_h_actual = y1 - y0
                    block_w_actual = x1 - x0
                    bytes_per_row = width * 3
                    
                    block_data = b""
                    for y in range(y0, y1):
                        start = y * bytes_per_row + x0 * 3
                        end = start + block_w_actual * 3
                        block_data += frame[start:end]
                    
                    if compress:
                        block_data = zlib.compress(block_data)
                    
                    blocks.append(block_data)
                
                packet = FramePacket(
                    frame_id=frame_id,
                    block_id=batch_ids[0] if batch_ids else 0,
                    cols=cols,
                    rows=rows,
                    block_w=block_w,
                    block_h=block_h,
                    width=width,
                    height=height,
                    total_blocks=total_blocks,
                    is_delta=is_delta,
                    compressed=compress,
                    blocks=blocks,
                    blocks_in_packet=len(blocks),
                    timestamp=time.time(),
                )
                
                encoded = encode_frame_packet(packet)
                self.sock.sendto(encoded, self.addr)
            
            self.prev_frame = frame
            return None
        
        except Exception as e:
            return ParseResult(False, error=f"Send frame failed: {str(e)}", code="SEND_FRAME_ERROR")
    
    def send_ping(self):
        """Send a PING packet."""
        data = encode_packet(PACKET_TYPE_PING)
        self.sock.sendto(data, self.addr)
    
    def send_pong(self, timestamp: float = 0.0):
        """Send a PONG packet."""
        ts = timestamp if timestamp != 0.0 else time.time()
        data = encode_packet(PACKET_TYPE_PONG, timestamp=ts)
        self.sock.sendto(data, self.addr)
    
    def send_eos(self):
        """Send an End-of-Stream packet."""
        data = encode_packet(PACKET_TYPE_EOS)
        self.sock.sendto(data, self.addr)
    
    def receive(self, timeout: float = 0.5) -> Optional[dict]:
        """Receive a packet (non-blocking)."""
        if not self.sock:
            return None
        
        self.sock.setblocking(False)
        try:
            self.sock.settimeout(timeout)
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            if data:
                return decode_packet(data)
        except socket.timeout:
            pass
        except BlockingIOError:
            pass
        return None
    
    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None


class UDPReceiver:
    def __init__(
        self,
        host_or_dsn: Optional[Union[str, FrameAddress]] = None,
        port: Optional[int] = None,
        *,
        dsn: Optional[str] = None,
        address: Optional[FrameAddress] = None,
        frame_received_callback: Optional[Callable] = None,
        idle_callback: Optional[Callable] = None,
        local_port: int = 0,
        blocking: bool = True,
        timeout: float = 0.5,
    ):
        """
        UDP Receiver with flexible constructor.
        
        Old API: UDPReceiver("127.0.0.1", 4200)
        New API: UDPReceiver(dsn="udp://127.0.0.1:4200/")
        """
        self.blocking = blocking
        self.timeout = timeout
        self.frame_received_callback = frame_received_callback
        self.idle_callback = idle_callback
        self.sock: Optional[socket.socket] = None
        self.error: Optional[ParseResult] = None
        self.address: Optional[FrameAddress] = None
        
        self.frames: Dict[int, Dict[int, bytes]] = defaultdict(dict)
        self.frame_meta: Dict[int, Dict] = {}
        self.prev_frame: Optional[bytes] = None
        self.prev_frame_meta: Dict = {}
        self.last_displayed_frame_id = -1
        self.running = False
        
        # Validate arguments
        result = self._validate_and_normalize_args(host_or_dsn, port, dsn, address)
        if not result.success:
            self.error = result
            return
        
        self.address = result.value
        self._setup_server(local_port)
    
    @staticmethod
    def _validate_and_normalize_args(
        host_or_dsn: Optional[Union[str, FrameAddress]],
        port: Optional[int],
        dsn: Optional[str],
        address: Optional[FrameAddress],
    ) -> ParseResult:
        """Validate and convert arguments to FrameAddress."""
        
        arg_count = sum([
            host_or_dsn is not None,
            port is not None,
            dsn is not None,
            address is not None,
        ])
        
        if arg_count == 0:
            # Default: listen on all interfaces, port specified in address
            return ParseResult(True, value=None)
        
        if address is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix address object with other args", code="AMBIGUOUS_ARGS")
            return address.validate()
        
        if dsn is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix dsn with other args", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(dsn)
        
        if isinstance(host_or_dsn, str) and host_or_dsn.startswith(("tcp://", "udp://", "unix://", "ws://", "wss://")):
            if port is not None:
                return ParseResult(False, error="Cannot specify port with DSN string", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(host_or_dsn)
        
        if isinstance(host_or_dsn, str) and port is not None:
            from .frame_address import FrameScheme
            address = FrameAddress(
                scheme=FrameScheme.UDP,
                host=host_or_dsn,
                port=port,
                socket_path=None,
                user=None,
                password=None,
                path="/",
            )
            return address.validate()
        
        if isinstance(host_or_dsn, str) and port is None:
            return ParseResult(False, error="Port required when host provided", code="MISSING_PORT")
        
        return ParseResult(False, error="Invalid arguments", code="INVALID_ARGS")
    
    def _setup_server(self, local_port: int = 0):
        """Setup server socket and bind."""
        if self.error:
            return
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 10 * 1024 * 1024)
            
            bind_port = local_port if local_port > 0 else (self.address.port if self.address else 0)
            self.sock.bind(("0.0.0.0", bind_port))
            
            if not self.blocking:
                self.sock.setblocking(False)
            
            self.sock.settimeout(self.timeout)
        except Exception as e:
            self.error = ParseResult(False, error=f"Server setup failed: {str(e)}", code="SERVER_SETUP_ERROR")
    
    def start_listening(self):
        """Start listening for frames in a loop."""
        self.running = True
        try:
            while self.running:
                self.receive()
                
                if self.idle_callback:
                    if not self.idle_callback():
                        break
        finally:
            self.close()
    
    def receive(self) -> Any:
        """Receive and reassemble frames."""
        if self.error or not self.sock:
            return None
        
        try:
            self.sock.settimeout(self.timeout)
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
        except socket.timeout:
            return None
        except BlockingIOError:
            return None
        
        if not data:
            return None
        
        packet_type_raw = struct.unpack("!B", data[:1])[0]
        
        if packet_type_raw == PACKET_TYPE_PING:
            self.send_pong()
            return PING
        elif packet_type_raw == PACKET_TYPE_PONG:
            return PONG
        elif packet_type_raw == PACKET_TYPE_EOS:
            return EOS
        elif packet_type_raw == PACKET_TYPE_FRAME:
            return self._handle_frame_packet(data)
        
        return None
    
    def _handle_frame_packet(self, data: bytes) -> Optional[bytes]:
        """Handle an incoming frame packet and reassemble if complete."""
        try:
            packet = decode_frame_packet(data)
        except Exception as e:
            logging.warning(f"Failed to decode frame packet: {e}")
            return None
        
        frame_id = packet.frame_id
        cols = packet.cols
        rows = packet.rows
        block_w = packet.block_w
        block_h = packet.block_h
        width = packet.width
        height = packet.height
        total_blocks = packet.total_blocks
        is_delta = packet.is_delta
        compressed = packet.compressed
        
        if frame_id in self.frame_meta:
            old_meta = self.frame_meta[frame_id]
            if (old_meta["width"] != width or old_meta["height"] != height or 
                old_meta["total_blocks"] != total_blocks):
                logging.warning(f"Frame {frame_id} dimensions changed, discarding old data")
                if frame_id in self.frames:
                    del self.frames[frame_id]
                self.prev_frame = None
                is_delta = False
        
        self.frame_meta[frame_id] = {
            "cols": cols,
            "rows": rows,
            "block_w": block_w,
            "block_h": block_h,
            "width": width,
            "height": height,
            "total_blocks": total_blocks,
            "is_delta": is_delta,
            "compressed": compressed,
        }
        
        for i, block_data in enumerate(packet.blocks):
            block_id = packet.block_id + i
            
            if compressed:
                try:
                    block_data = zlib.decompress(block_data)
                except zlib.error as e:
                    logging.warning(f"Failed to decompress block {block_id}: {e}")
                    continue
            
            self.frames[frame_id][block_id] = block_data
        
        received_count = len(self.frames[frame_id])
        
        if received_count >= total_blocks:
            return self._reassemble_frame(frame_id)
        
        return None
    
    def _reassemble_frame(self, frame_id: int) -> Optional[bytes]:
        """Reassemble a complete frame from chunks (returns bytes)."""
        if frame_id not in self.frames:
            return None
        
        meta = self.frame_meta[frame_id]
        cols = meta["cols"]
        block_w = meta["block_w"]
        block_h = meta["block_h"]
        width = meta["width"]
        height = meta["height"]
        total_blocks = meta["total_blocks"]
        is_delta = meta["is_delta"]
        
        blocks = self.frames[frame_id]
        
        # Create frame as bytes
        bytes_per_row = width * 3
        if is_delta and self.prev_frame is not None and len(self.prev_frame) == height * bytes_per_row:
            full_frame_bytes = bytearray(self.prev_frame)
        else:
            full_frame_bytes = bytearray(height * bytes_per_row)
        
        for block_id, block_data in blocks.items():
            if block_id >= total_blocks:
                logging.warning(f"Skipping block {block_id}: exceeds total_blocks {total_blocks}")
                continue
            
            row = block_id // cols
            col = block_id % cols
            x = col * block_w
            y = row * block_h
            
            actual_block_w = min(block_w, width - x)
            actual_block_h = min(block_h, height - y)
            
            if actual_block_h <= 0 or actual_block_w <= 0:
                logging.warning(f"Skipping block {block_id}: invalid dimensions")
                continue
            
            expected_size = actual_block_h * actual_block_w * 3
            if len(block_data) != expected_size:
                logging.warning(f"Skipping block {block_id}: size mismatch")
                continue
            
            for by in range(actual_block_h):
                dst_offset = (y + by) * bytes_per_row + x * 3
                src_offset = by * actual_block_w * 3
                full_frame_bytes[dst_offset:dst_offset + actual_block_w * 3] = block_data[src_offset:src_offset + actual_block_w * 3]
        
        del self.frames[frame_id]
        self.frame_meta.pop(frame_id, None)
        
        self.prev_frame = bytes(full_frame_bytes)
        self.prev_frame_meta = meta
        
        if self.frame_received_callback:
            self.frame_received_callback(self.prev_frame, frame_id)
        
        return self.prev_frame
    
    def send_pong(self, timestamp: float = 0.0):
        """Send a PONG response."""
        if not self.sock:
            return
        ts = timestamp if timestamp != 0.0 else time.time()
        data = encode_packet(PACKET_TYPE_PONG, timestamp=ts)
        # Send back to broadcast address (not ideal, but simple)
        self.sock.sendto(data, ("255.255.255.255", self.address.port if self.address else 4200))
    
    def close(self):
        self.running = False
        if self.sock:
            self.sock.close()
            self.sock = None
