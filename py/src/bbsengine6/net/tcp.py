# bbsengine6/net/tcp.py
# TCP sender/receiver classes with frame transmission support

import socket
import struct
import time
import zlib
import math
from typing import Optional, Union

from .packet import Packet
from .frame import (
    FramePacket,
    encode_frame_packet,
    FRAME_PACKET_HEADER_SIZE,
)
from .frame_address import FrameAddress, FrameAddressParser, ParseResult


def _calc_optimal_blocks_per_packet(block_w: int, block_h: int, compress: bool) -> int:
    """Calculate max blocks that fit in TCP packet."""
    TCP_MAX_PAYLOAD = 65507 - FRAME_PACKET_HEADER_SIZE
    block_size = block_w * block_h * 3
    if compress:
        block_size = max(block_size // 10, 100)
    return max(1, TCP_MAX_PAYLOAD // block_size)


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


class TCPSender:
    def __init__(
        self,
        host_or_dsn: Optional[Union[str, FrameAddress]] = None,
        port: Optional[int] = None,
        *,
        dsn: Optional[str] = None,
        address: Optional[FrameAddress] = None,
    ):
        """
        TCP Sender with flexible constructor supporting multiple calling patterns.
        
        Old API (backward compatible):
            TCPSender("example.com", 4200)
            TCPSender(host="example.com", port=4200)
        
        New DSN API:
            TCPSender("tcp://example.com:4200/")
            TCPSender(dsn="tcp://example.com:4200/")
            TCPSender(address=FrameAddress(...))
        
        Error handling: returns ParseResult in self.error if validation fails.
        """
        self.address: Optional[FrameAddress] = None
        self.error: Optional[ParseResult] = None
        self.sock: Optional[socket.socket] = None
        self.prev_frame = None
        
        # Validate and normalize arguments
        result = self._validate_and_normalize_args(host_or_dsn, port, dsn, address)
        if not result.success:
            self.error = result
            return
        
        self.address = result.value
    
    @staticmethod
    def _validate_and_normalize_args(
        host_or_dsn: Optional[Union[str, FrameAddress]],
        port: Optional[int],
        dsn: Optional[str],
        address: Optional[FrameAddress],
    ) -> ParseResult:
        """Validate and convert arguments to FrameAddress."""
        
        # Count how many argument types provided
        arg_count = sum([
            host_or_dsn is not None,
            port is not None,
            dsn is not None,
            address is not None,
        ])
        
        if arg_count == 0:
            return ParseResult(False, error="No connection parameters provided", code="NO_ARGS")
        
        # Case 1: FrameAddress object provided
        if address is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix address object with other args", code="AMBIGUOUS_ARGS")
            return address.validate()
        
        # Case 2: DSN string provided (via dsn kwarg)
        if dsn is not None:
            if arg_count > 1:
                return ParseResult(False, error="Cannot mix dsn with other args", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(dsn)
        
        # Case 3: DSN string as first positional arg (detect by checking if starts with scheme)
        if isinstance(host_or_dsn, str) and host_or_dsn.startswith(("tcp://", "udp://", "unix://", "ws://", "wss://")):
            if port is not None:
                return ParseResult(False, error="Cannot specify port with DSN string", code="AMBIGUOUS_ARGS")
            return FrameAddressParser.parse(host_or_dsn)
        
        # Case 4: Old-style API (host, port)
        if isinstance(host_or_dsn, str) and port is not None:
            # Create FrameAddress from host/port
            from .frame_address import FrameScheme
            address = FrameAddress(
                scheme=FrameScheme.TCP,
                host=host_or_dsn,
                port=port,
                socket_path=None,
                user=None,
                password=None,
                path="/",
            )
            return address.validate()
        
        # Case 5: Old-style API with only host_or_dsn (positional, not DSN)
        if isinstance(host_or_dsn, str) and port is None:
            return ParseResult(False, error="Port required when host provided", code="MISSING_PORT")
        
        return ParseResult(False, error="Invalid arguments", code="INVALID_ARGS")
    
    def connect(self) -> Optional[ParseResult]:
        """Connect to remote host. Returns error if not successful."""
        if self.error:
            return self.error
        
        if self.address is None:
            return ParseResult(False, error="No address configured", code="NO_ADDRESS")
        
        if self.sock is not None:
            return None  # Already connected
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Apply timeout if specified
            if self.address.timeout:
                self.sock.settimeout(self.address.timeout)
            self.sock.connect((self.address.host, self.address.port))
            return None
        except Exception as e:
            return ParseResult(False, error=f"Connection failed: {str(e)}", code="CONNECT_ERROR")
    
    def send(self, packet: Packet) -> Optional[ParseResult]:
        """Send packet. Returns error if not successful."""
        if self.error:
            return self.error
        
        if self.sock is None:
            conn_error = self.connect()
            if conn_error:
                return conn_error
        
        try:
            self.sock.sendall(packet.encode())
            return None
        except Exception as e:
            return ParseResult(False, error=f"Send failed: {str(e)}", code="SEND_ERROR")
    
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
        """
        Send frame. Returns error if not successful.
        
        Args:
            frame: Raw frame bytes
            frame_id: Unique frame identifier
            prev_frame: Previous frame for delta detection
            cols, rows: Grid dimensions (auto-calculated if not provided)
            compress: Enable zlib compression
            full_frame: If True, send all blocks (not just changes)
            auto_batch: If True, automatically batch blocks to fill TCP packets
            is_delta: Explicit delta flag. If None, auto-detect from prev_frame.
        """
        if self.error:
            return self.error
        
        if self.sock is None:
            conn_error = self.connect()
            if conn_error:
                return conn_error
        
        try:
            # Assume frame is bytes with dimensions encoded somehow
            # For now, use a simple heuristic
            if isinstance(frame, bytes):
                frame_size = len(frame)
                # Common sizes: 1920x1080x3 = 6220800 bytes
                # 640x480x3 = 921600 bytes
                # 320x240x3 = 230400 bytes
                if frame_size == 6220800:
                    width, height = 1920, 1080
                elif frame_size == 921600:
                    width, height = 640, 480
                elif frame_size == 230400:
                    width, height = 320, 240
                else:
                    # Try to estimate
                    pixels = frame_size // 3
                    width = int(math.sqrt(pixels))
                    height = pixels // width
            else:
                # Assume tuple/list of (width, height) appended or dict
                raise ValueError("Frame must be bytes for now")
            
            # Determine delta mode
            if is_delta is None:
                is_delta = not full_frame and prev_frame is not None and _detect_delta(frame, prev_frame)
            
            # Calculate grid if not provided
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
            
            # Build blocks list
            if is_delta and prev_frame is not None:
                # For delta, we'd need to compare blocks
                # Simple approach: send all for now
                block_ids = list(range(total_blocks))
            else:
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
                    
                    # Extract block from frame bytes
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
                self.sock.sendall(encoded)
            
            self.prev_frame = frame
            return None
        
        except Exception as e:
            return ParseResult(False, error=f"Send frame failed: {str(e)}", code="SEND_FRAME_ERROR")
    
    def recv(self) -> Union[Optional[Packet], ParseResult]:
        """Receive packet. Returns packet or error ParseResult."""
        if self.error:
            return self.error
        
        if self.sock is None:
            return ParseResult(False, error="Not connected", code="NOT_CONNECTED")
        
        try:
            return Packet.recv(self.sock)
        except Exception as e:
            return ParseResult(False, error=f"Receive failed: {str(e)}", code="RECV_ERROR")
    
    def close(self):
        """Close connection."""
        if self.sock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.sock.close()
            self.sock = None


class TCPReceiver:
    def __init__(
        self,
        host_or_dsn: Optional[Union[str, FrameAddress]] = None,
        port: Optional[int] = None,
        *,
        dsn: Optional[str] = None,
        address: Optional[FrameAddress] = None,
        blocking: bool = False,
        timeout: float = 1.0,
    ):
        """
        TCP Receiver with flexible constructor.
        
        Old API: TCPReceiver("127.0.0.1", 4200)
        New API: TCPReceiver(dsn="tcp://127.0.0.1:4200/")
        """
        self.blocking = blocking
        self.timeout = timeout
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.error: Optional[ParseResult] = None
        self.address: Optional[FrameAddress] = None
        
        # Validate and normalize arguments
        result = TCPSender._validate_and_normalize_args(host_or_dsn, port, dsn, address)
        if not result.success:
            self.error = result
            return
        
        self.address = result.value
        self._setup_server()
    
    def _setup_server(self):
        """Setup server socket and bind."""
        if self.address is None or self.error:
            return
        
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.address.host, self.address.port))
            self.server_sock.listen(1)
            timeout_val = self.timeout if not self.blocking else None
            self.server_sock.settimeout(timeout_val)
            self._accept_connection()
        except Exception as e:
            self.error = ParseResult(False, error=f"Server setup failed: {str(e)}", code="SERVER_SETUP_ERROR")
    
    def _accept_connection(self):
        """Accept incoming TCP connection."""
        if self.client_sock is None and self.server_sock:
            try:
                self.client_sock, addr = self.server_sock.accept()
                timeout_val = self.timeout if not self.blocking else None
                self.client_sock.settimeout(timeout_val)
            except socket.timeout:
                pass
            except Exception as e:
                self.error = ParseResult(False, error=f"Accept failed: {str(e)}", code="ACCEPT_ERROR")
    
    def receive(self) -> Union[Optional[FramePacket], ParseResult]:
        """Receive a frame packet."""
        if self.error:
            return self.error
        
        if self.client_sock is None:
            try:
                self._accept_connection()
            except socket.timeout:
                return None
        
        try:
            header = self._recv_exact(FRAME_PACKET_HEADER_SIZE)
            if header is None:
                return None
            
            (
                frame_id,
                block_id,
                cols,
                rows,
                block_w,
                block_h,
                width,
                height,
                total_blocks,
                flags,
                blocks_in_packet,
                timestamp,
            ) = struct.unpack("!I I H H H H H H I ? I d", header)
            
            is_delta = bool(flags & 0x01)
            compressed = bool(flags & 0x02)
            
            blocks = []
            for _ in range(blocks_in_packet):
                block_len_bytes = self._recv_exact(4)
                if block_len_bytes is None:
                    return None
                block_len = struct.unpack("!I", block_len_bytes)[0]
                
                block_data = self._recv_exact(block_len)
                if block_data is None:
                    return None
                
                if compressed:
                    block_data = zlib.decompress(block_data)
                
                blocks.append(block_data)
            
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
                is_delta=is_delta,
                compressed=compressed,
                blocks=blocks,
                blocks_in_packet=blocks_in_packet,
                timestamp=timestamp,
            )
        
        except socket.timeout:
            return None
        except Exception as e:
            self.client_sock = None
            return ParseResult(False, error=f"Receive failed: {str(e)}", code="RECV_ERROR")
    
    def _recv_exact(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes from socket."""
        if self.client_sock is None:
            return None
        
        data = b""
        while len(data) < n:
            try:
                chunk = self.client_sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                return None
        return data
    
    def close(self):
        """Close all sockets."""
        if self.client_sock:
            try:
                self.client_sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.client_sock.close()
            self.client_sock = None
        
        if self.server_sock:
            self.server_sock.close()
            self.server_sock = None
