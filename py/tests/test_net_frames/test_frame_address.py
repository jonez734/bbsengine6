# tests/test_net/test_frame_address.py
# Tests for DSN frame address parsing

from bbsengine6.net import FrameAddressParser, FrameScheme


class TestFrameAddressParsing:
    """Tests for frame address parsing."""

    def test_parse_tcp_basic(self):
        """Parse basic TCP address."""
        result = FrameAddressParser.parse("tcp://host:4200/")
        assert result.success
        assert result.value.scheme == FrameScheme.TCP
        assert result.value.host == "host"
        assert result.value.port == 4200

    def test_parse_tcp_default_port(self):
        """TCP defaults to port 4200."""
        result = FrameAddressParser.parse("tcp://host/")
        assert result.success
        assert result.value.port == 4200

    def test_parse_udp(self):
        """Parse UDP address."""
        result = FrameAddressParser.parse("udp://host:4200/")
        assert result.success
        assert result.value.scheme == FrameScheme.UDP

    def test_parse_with_credentials(self):
        """Parse address with username and password."""
        result = FrameAddressParser.parse("tcp://user:pass@host:4200/")
        assert result.success
        assert result.value.user == "user"
        assert result.value.password == "pass"

    def test_parse_with_path(self):
        """Parse address with path."""
        result = FrameAddressParser.parse("tcp://host:4200/camera/1")
        assert result.success
        assert result.value.path == "/camera/1"

    def test_parse_with_query(self):
        """Parse address with query parameters."""
        result = FrameAddressParser.parse("tcp://host:4200/?timeout=30&retry=3")
        assert result.success
        assert result.value.timeout == 30
        assert result.value.retry == 3

    def test_parse_with_custom_params(self):
        """Custom query parameters passed through."""
        result = FrameAddressParser.parse("tcp://host:4200/?timeout=30&custom=val")
        assert result.success
        assert result.value.custom_params == {"custom": "val"}

    def test_parse_unix_socket(self):
        """Parse unix socket address."""
        result = FrameAddressParser.parse("unix:///run/frame.sock")
        assert result.success
        assert result.value.scheme == FrameScheme.UNIX
        assert result.value.socket_path == "/run/frame.sock"
        assert result.value.host is None
        assert result.value.port is None

    def test_parse_ws(self):
        """Parse WebSocket address."""
        result = FrameAddressParser.parse("ws://host:80/chat")
        assert result.success
        assert result.value.scheme == FrameScheme.WS
        assert result.value.port == 80

    def test_parse_wss_default_port(self):
        """WSS defaults to port 443."""
        result = FrameAddressParser.parse("wss://host/")
        assert result.success
        assert result.value.port == 443


class TestFrameAddressErrors:
    """Tests for frame address error handling."""

    def test_invalid_scheme(self):
        """Invalid scheme rejected."""
        result = FrameAddressParser.parse("ftp://host:4200/")
        assert not result.success
        assert result.code == "INVALID_SCHEME"

    def test_invalid_port_range(self):
        """Port out of range rejected."""
        result = FrameAddressParser.parse("tcp://host:99999/")
        assert not result.success
        assert result.code == "INVALID_PORT"

    def test_invalid_port_string(self):
        """Non-numeric port rejected."""
        result = FrameAddressParser.parse("tcp://host:abc/")
        assert not result.success
        assert result.code == "INVALID_PORT"

    def test_unix_socket_with_port_error(self):
        """Unix socket with port rejected."""
        result = FrameAddressParser.parse("unix:///path:4200")
        assert not result.success
        assert result.code == "PORT_NOT_ALLOWED"

    def test_unix_relative_path_error(self):
        """Unix socket relative path rejected."""
        result = FrameAddressParser.parse("unix://./relative/path")
        assert not result.success
        assert result.code == "INVALID_UNIX_PATH"

    def test_missing_host_tcp(self):
        """TCP requires host."""
        result = FrameAddressParser.parse("tcp://:4200/")
        assert not result.success

    def test_invalid_timeout_param(self):
        """Invalid timeout rejected."""
        result = FrameAddressParser.parse("tcp://host/?timeout=abc")
        assert not result.success
        assert result.code == "INVALID_TIMEOUT"

    def test_invalid_retry_negative(self):
        """Negative retry rejected."""
        result = FrameAddressParser.parse("tcp://host/?retry=-1")
        assert not result.success


class TestFrameAddressRoundTrip:
    """Tests for roundtrip: parse -> to_string -> parse."""

    def test_roundtrip_tcp(self):
        """TCP address roundtrip."""
        dsn = "tcp://user:pass@host:4200/path?timeout=30&custom=val"
        result1 = FrameAddressParser.parse(dsn)
        assert result1.success

        dsn2 = result1.value.to_string()
        result2 = FrameAddressParser.parse(dsn2)
        assert result2.success

        assert result1.value.host == result2.value.host
        assert result1.value.port == result2.value.port
        assert result1.value.timeout == result2.value.timeout

    def test_roundtrip_unix(self):
        """Unix socket roundtrip."""
        dsn = "unix:///run/frame.sock"
        result1 = FrameAddressParser.parse(dsn)
        assert result1.success

        dsn2 = result1.value.to_string()
        result2 = FrameAddressParser.parse(dsn2)
        assert result2.success
        assert result1.value.socket_path == result2.value.socket_path
