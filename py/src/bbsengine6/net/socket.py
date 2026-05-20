# asimov/net/socket.py
# Socket helpers for TCP/UDP communication

import socket
import struct
from typing import Optional, Tuple


def recv_all(sock: socket.socket, length: int) -> Optional[bytes]:
    """Receive exactly `length` bytes from a TCP socket, or None if closed."""
    data = bytearray()
    while len(data) < length:
        try:
            chunk = sock.recv(length - len(data))
        except socket.error as e:
            print(f"recv_all(): socket error: {e}")
            return None
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def recv_udp(
    sock: socket.socket, bufsize: int = 4096
) -> Tuple[Optional[bytes], Optional[Tuple[str, int]]]:
    """Receive a single datagram from a UDP socket."""
    try:
        data, addr = sock.recvfrom(bufsize)
        return data, addr
    except socket.error as e:
        print(f"recv_udp(): socket error: {e}")
        return None, None


def send_with_length(conn: socket.socket, payload: bytes):
    """
    Send a length-prefixed payload (4-byte big-endian length + data).
    This allows TCP packets larger than typical buffer sizes to be sent
    while keeping the connection open for multiple messages.
    """
    length_prefix = struct.pack("!I", len(payload))
    conn.sendall(length_prefix + payload)


def recv_with_length(conn: socket.socket) -> bytes:
    """
    Receive a length-prefixed payload.
    First reads 4 bytes for the length, then reads exactly that many bytes.
    """

    def recv_exactly(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise EOFError("Connection closed before full payload received")
            buf += chunk
        return buf

    length_bytes = recv_exactly(4)
    (length,) = struct.unpack("!I", length_bytes)
    return recv_exactly(length)


def retry_until_connected(
    host: str, port: int, retries: int = 5, delay: float = 0.2
) -> socket.socket:
    """
    Attempt to connect to a TCP host:port, retrying `retries` times with `delay` seconds between attempts.
    Returns a connected socket, or raises the last exception if all retries fail.
    """
    import time

    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            return sock
        except Exception as e:
            last_exc = e
            print(
                f"[tcp_connect_retry] Attempt {attempt} failed, retrying in {delay}s..."
            )
            time.sleep(delay)
    raise last_exc
