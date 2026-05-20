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
        """Send frame over TCP and receive it."""
        frame_data = bytes(range(256)) * 300  # 640x480 frame
        frame = Frame(frame_data, 640, 480, frame_id=1)
        
        receiver = TCPReceiver("127.0.0.1", free_port, timeout=2.0)
        
        # Run receiver in thread
        def recv_thread():
            received = receiver.receive()
            assert received is not None
            assert isinstance(received, type(receiver.receive.__annotations__.get('return')))
        
        thread = threading.Thread(target=recv_thread, daemon=True)
        thread.start()
        
        # Give receiver time to bind
        time.sleep(0.1)
        
        sender = TCPSender("127.0.0.1", free_port)
        error = sender.connect()
        assert error is None
        
        error = sender.send_frame(frame)
        assert error is None
        
        thread.join(timeout=2.0)
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
