# tests/test_net/conftest.py
# Shared fixtures for frame transmission and notification tests

import pytest
import socket
import threading
import time
from typing import Optional


@pytest.fixture
def small_frame_bytes():
    """Generate small test frame (64x64 RGB)."""
    return bytes(range(256)) * (64 * 64 * 3 // 256)


@pytest.fixture
def medium_frame_bytes():
    """Generate medium test frame (640x480 RGB)."""
    return bytes(range(256)) * (640 * 480 * 3 // 256)


@pytest.fixture
def large_frame_bytes():
    """Generate large test frame (1920x1080 RGB)."""
    return bytes(range(256)) * (1920 * 1080 * 3 // 256)


@pytest.fixture
def free_port():
    """Get a free port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def localhost_address(free_port):
    """Return localhost address tuple."""
    return ('127.0.0.1', free_port)


class FrameReceiverThread:
    """Helper for running frame receiver in thread."""
    
    def __init__(self, receiver_class, host, port, timeout=2.0):
        self.receiver_class = receiver_class
        self.host = host
        self.port = port
        self.timeout = timeout
        self.receiver = None
        self.thread = None
        self.frames = []
        self.errors = []
    
    def on_frame(self, frame, frame_id):
        """Callback for frame reception."""
        self.frames.append((frame, frame_id))
    
    def on_idle(self):
        """Callback for idle time."""
        return True
    
    def start(self):
        """Start receiver in background thread."""
        def run():
            try:
                self.receiver = self.receiver_class(
                    self.host,
                    self.port,
                    frame_received_callback=self.on_frame,
                    idle_callback=self.on_idle,
                    timeout=self.timeout,
                )
                if not self.receiver.error:
                    self.receiver.start_listening()
            except Exception as e:
                self.errors.append(e)
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        time.sleep(0.1)  # Give receiver time to start
    
    def stop(self):
        """Stop receiver."""
        if self.receiver:
            self.receiver.close()
        if self.thread:
            self.thread.join(timeout=1.0)


@pytest.fixture
def receiver_thread_factory():
    """Factory for creating receiver threads."""
    return FrameReceiverThread
