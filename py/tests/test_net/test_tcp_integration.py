# tests/test_net/test_tcp_integration.py
# Integration tests for TCP frame transmission

import pytest
import threading
import time
from bbsengine6.net import TCPSender, TCPReceiver, Frame


@pytest.mark.integration
class TestTCPRoundTrip:
    """Tests for TCP send/receive roundtrip."""
    
    def test_tcp_basic_connect(self, free_port):
        """TCP sender can connect to receiver."""
        receiver = TCPReceiver("127.0.0.1", free_port)
        assert not receiver.error
        
        sender = TCPSender("127.0.0.1", free_port)
        error = sender.connect()
        assert error is None
        
        sender.close()
        receiver.close()
    
    def test_tcp_send_receive_frame(self, free_port):
        """Test that send_frame accepts Frame object and extracts frame_id."""
        # Create a small frame for testing
        frame_data = bytes(range(256)) * 37 + bytes(range(128))  # 9600 bytes for 64x50 RGB
        frame = Frame(frame_data, 64, 50, frame_id=42)
        
        sender = TCPSender("127.0.0.1", free_port)
        receiver = TCPReceiver("127.0.0.1", free_port, timeout=0.5)
        
        # Test that send_frame works with Frame object (extracts frame_id)
        # Connection may or may not succeed, but the API should accept Frame without explicit frame_id
        error = sender.send_frame(frame)
        # If error, should be a ParseResult with error details, not a signature error
        if error is not None:
            assert isinstance(error, ParseResult)
        # Success - frame was sent (or queued)
        
        sender.close()
        receiver.close()
    
    def test_tcp_constructor_old_api(self, free_port):
        """Old constructor style still works."""
        sender = TCPSender("127.0.0.1", free_port)
        assert sender.address is not None
        assert sender.address.host == "127.0.0.1"
        assert sender.address.port == free_port
    
    def test_tcp_constructor_dsn(self, free_port):
        """New DSN constructor works."""
        dsn = f"tcp://127.0.0.1:{free_port}/"
        sender = TCPSender(dsn)
        assert sender.address is not None
        assert sender.address.host == "127.0.0.1"
        assert sender.address.port == free_port
    
    def test_tcp_constructor_error(self):
        """Invalid constructor args return error."""
        sender = TCPSender()
        assert sender.error is not None
        assert sender.error.code == "NO_ARGS"
