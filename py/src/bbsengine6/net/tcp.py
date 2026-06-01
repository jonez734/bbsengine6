# bbsengine6/net/tcp.py
# TCP sender/receiver classes
# Copied from asimov.net (bbsengine6 is not permitted to import from asimov)

import socket
import struct
import time
from typing import Optional, Union

from .frame_address import FrameAddress, FrameAddressParser, ParseResult
from .frame_types import Frame, NumpyFrame, frame_from_any


class TCPSender:
    def __init__(
        self,
        host_or_dsn: Optional[Union[str, FrameAddress]] = None,
        port: Optional[int] = None,
        *,
        dsn: Optional[str] = None,
        address: Optional[FrameAddress] = None,
    ):
        self.address: Optional[FrameAddress] = None
        self.error: Optional[ParseResult] = None
        self.sock: Optional[socket.socket] = None
        self.prev_frame: Optional[Union[Frame, NumpyFrame]] = None

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
                scheme=FrameScheme.TCP,
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

    def connect(self) -> Optional[ParseResult]:
        if self.error:
            return self.error

        if self.address is None:
            return ParseResult(False, error="No address configured", code="NO_ADDRESS")

        if self.sock is not None:
            return None

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if self.address.timeout:
                self.sock.settimeout(self.address.timeout)
            self.sock.connect((self.address.host, self.address.port))
            return None
        except Exception as e:
            return ParseResult(False, error=f"Connection failed: {str(e)}", code="CONNECT_ERROR")

    def send(self, packet) -> Optional[ParseResult]:
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
        frame: Union[bytes, Frame, NumpyFrame, object],
        frame_id: Optional[int] = None,
    ) -> Optional[ParseResult]:
        return None

    def recv(self) -> Union[Optional[object], ParseResult]:
        if self.error:
            return self.error

        if self.sock is None:
            return ParseResult(False, error="Not connected", code="NOT_CONNECTED")

        try:
            from .socket import recv_all
            header = recv_all(self.sock, 16)
            if header is None:
                return None
            ptype, timestamp, payload_len = struct.unpack("!IdI", header)
            payload = recv_all(self.sock, payload_len)
            if payload is None:
                return None
            from .packet import Packet as BbsPacket
            return BbsPacket(ptype, payload, timestamp)
        except Exception as e:
            return ParseResult(False, error=f"Receive failed: {str(e)}", code="RECV_ERROR")

    def close(self):
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
        self.blocking = blocking
        self.timeout = timeout
        self.server_sock: Optional[socket.socket] = None
        self.client_sock: Optional[socket.socket] = None
        self.error: Optional[ParseResult] = None
        self.address: Optional[FrameAddress] = None

        result = TCPSender._validate_and_normalize_args(host_or_dsn, port, dsn, address)
        if not result.success:
            self.error = result
            return

        self.address = result.value
        self._setup_server()

    def _setup_server(self):
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
        if self.client_sock is None and self.server_sock:
            try:
                self.client_sock, addr = self.server_sock.accept()
                timeout_val = self.timeout if not self.blocking else None
                self.client_sock.settimeout(timeout_val)
            except socket.timeout:
                pass
            except Exception as e:
                self.error = ParseResult(False, error=f"Accept failed: {str(e)}", code="ACCEPT_ERROR")

    def recv(self) -> Union[Optional[object], ParseResult]:
        if self.error:
            return self.error

        if self.client_sock is None:
            self._accept_connection()
            if self.client_sock is None:
                return None

        try:
            from .socket import recv_all
            header = recv_all(self.client_sock, 16)
            if header is None:
                self.client_sock = None
                return None
            ptype, timestamp, payload_len = struct.unpack("!IdI", header)
            payload = recv_all(self.client_sock, payload_len)
            if payload is None:
                self.client_sock = None
                return None
            from .packet import Packet as BbsPacket
            return BbsPacket(ptype, payload, timestamp)
        except socket.timeout:
            return None
        except Exception as e:
            self.client_sock = None
            return ParseResult(False, error=f"Receive failed: {str(e)}", code="RECV_ERROR")

    def close(self):
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