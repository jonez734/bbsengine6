# bbsengine6/net/conf.py
# Unified network configuration for frame transmission and notifications

# Frame transmission constants (from asimov)
CHUNK_SIZE = 64
DEFAULT_PORT = 4200  # Updated from asimov's 5000 to 4200
COMPRESSION_ENABLED = False
BUFFER_SIZE = 65507

TCP_BUFFER_SIZE = 8192
UDP_BUFFER_SIZE = 65507

RETRY_DELAY = 0.2
RETRY_COUNT = 5

# Service endpoints (frame transmission)
VIDEOCAPTURE_HOST = "127.0.0.1"
VIDEOCAPTURE_PORT = 4200
PROCESSING_HOST = "127.0.0.1"
PROCESSING_PORT = 4200
RENDER_HOST = "127.0.0.1"
RENDER_PORT = 4200
