# BBSEngine6 Net Module Specification

## Overview

The `bbsengine6.net` module is a unified networking layer supporting both:
- **Notification delivery**: SMTP-like inter-machine notifications using WebSocket
- **Frame transmission**: TCP/UDP binary frame transfer with advanced features

Both systems coexist peacefully, using separate addressing schemes and protocols.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
└─────────────────────────────────────────────────────────┘
          │                                      │
          ↓                                      ↓
┌──────────────────────────┐     ┌──────────────────────────┐
│  Notification System     │     │  Frame Transmission      │
│  (SMTP-like addressing)  │     │  (DSN-like addressing)   │
└──────────────────────────┘     └──────────────────────────┘
          │                                      │
          ├─→ AddressParser (user@machine)      │
          ├─→ InternetRouter                    │
          ├─→ MachineRegistry                   ├─→ FrameAddressParser (tcp://...)
          └─→ WebSocketTransport                ├─→ TCPSender/TCPReceiver
                                                ├─→ UDPSender/UDPReceiver
                                                └─→ Socket utilities

┌─────────────────────────────────────────────────────────┐
│               Network Layer (TCP/UDP/WebSocket)         │
└─────────────────────────────────────────────────────────┘
```

## Module Organization

### Configuration Layer
- **conf.py**: Constants for frame transmission and notifications
  - DEFAULT_PORT = 4200 (TCP/UDP)
  - Buffer sizes, retry settings, service endpoints

### Socket Layer
- **socket.py**: Low-level socket utilities
  - `recv_all(sock, length)` - Receive exact byte count
  - `recv_udp(sock, bufsize)` - Receive UDP datagram
  - `send_with_length(conn, payload)` - Send length-prefixed payload
  - `recv_with_length(conn)` - Receive length-prefixed payload
  - `retry_until_connected(host, port, retries, delay)` - Retry TCP connection

### Packet Protocol Layer
- **packet.py**: Generic packet types and encoding
  - `Packet` class: container for any packet data
  - `PING`, `PONG`, `EOS`: sentinel packet types
  - `encode_packet()`, `decode_packet()`: binary serialization
  - `register_packet_type()`: extensible type system

- **frame.py**: Video frame-specific packet types
  - `FramePacket`: dataclass for frame data
  - Support for delta encoding, compression, block batching
  - `encode_frame_packet()`, `decode_frame_packet()`: binary serialization

### Addressing Layer
- **frame_address.py**: RFC 3986 compliant frame address parser
  - Supports: `tcp://`, `udp://`, `unix://`, `ws://`, `wss://`
  - Query parameters with hybrid handling (see below)
  - Full validation and sanitization

- **address.py**: SMTP-like notification addressing
  - Supports: `user@machine` format
  - Distinguishes local, remote, and federated addresses

### Transport Layer
- **tcp.py**: TCP sender/receiver for reliable frame transmission
  - `TCPSender`: Connect and send frames with optional compression/batching
  - `TCPReceiver`: Listen and receive frames

- **udp.py**: UDP sender/receiver for fast frame transmission
  - `UDPSender`: Send frames across network
  - `UDPReceiver`: Listen, reassemble fragmented frames

- **transport.py**: WebSocket transport for notifications
  - `WebSocketTransport`: Async/sync WebSocket client
  - `WebSocketProtocol`: Handle incoming WebSocket notifications

### Service Layer
- **router.py**: Route mixed recipient types
  - `InternetRouter`: Classify and route notifications and frames
  - Detect frame vs notification addresses automatically

- **registry.py**: Machine registry for remote machine configs
  - `MachineRegistry`: PostgreSQL-backed registry
  - `MachineConfig`: Configuration for remote machines

- **integration.py**: Notification system integration
  - `NotifyIntegration`: Unified interface for local + remote notifications
  - Handles routing and delivery to appropriate transport

## Frame Addressing (DSN Format)

### Scheme Format

```
scheme://[user[:password]@]host[:port][/path][?query]
```

### Supported Schemes

| Scheme | Transport | Default Port | Use Case |
|--------|-----------|---|---|
| `tcp://` | TCP Socket | 4200 | Reliable, ordered delivery |
| `udp://` | UDP Socket | 4200 | Fast, stateless delivery |
| `unix://` | Unix Domain Socket | N/A | Local IPC |
| `ws://` | WebSocket | 80 | HTTP-compatible unencrypted |
| `wss://` | WebSocket Secure | 443 | HTTP-compatible encrypted |

### Examples

```
# TCP with default port
tcp://camera.local/

# TCP with explicit port and credentials
tcp://alice:secret@remote.host:4200/

# UDP multicast
udp://224.1.1.1:4200/

# Unix socket (absolute path only)
unix:///var/run/frame.sock

# WebSocket with path and query
ws://stream.example.com/camera/1/hires?quality=high&timeout=30

# Secure WebSocket
wss://secure.example.com:443/frames
```

### Query Parameters (Hybrid Approach)

**Transport layer interprets these standard parameters:**
- `timeout=N` - Connection timeout in seconds (int > 0)
- `retry=N` - Retry count (int >= 0)
- `keepalive=N` - Keepalive interval in seconds (int > 0)
- `backoff=F` - Exponential backoff factor (float > 1.0)

**Application layer receives everything else:**
- Custom parameters passed through in `FrameAddress.custom_params` dict
- Application decides how to interpret them
- Examples: `compression=zlib`, `format=h264`, `token=xyz123`

**Example:**
```python
address = FrameAddressParser.parse("tcp://host:4200/?timeout=30&compression=zlib")
# address.timeout = 30 (transport uses this)
# address.custom_params = {"compression": "zlib"} (app uses this)
```

### Error Handling

All parsing/validation returns `ParseResult` objects (no exceptions):

```python
result = FrameAddressParser.parse(dsn_string)
if not result.success:
    print(result.error)      # Human-readable error message
    print(result.code)       # Machine-readable error code
    # Possible codes: INVALID_SCHEME, INVALID_PORT, INVALID_HOST,
    #                 INVALID_UNIX_PATH, PORT_NOT_ALLOWED, etc.
```

## Notification Addressing (SMTP Format)

### Format

```
user@machine
```

### Types

- **Local**: `alice` (same machine)
- **Remote**: `bob@other.machine` (different machine, non-federated)
- **Federated**: `carol@remote.example.com` (fully qualified domain)

### Classification

```python
address = AddressParser("local.machine").parse("alice@remote.org")
# address.is_local() → False
# address.is_remote() → True
# address.is_federated() → True
```

## TCP Frame Transmission

### Sender Example

```python
from bbsengine6.net import TCPSender

# Old API (backward compatible)
sender = TCPSender("camera.local", 4200)

# New DSN API
sender = TCPSender("tcp://camera.local:4200/")

# Check for errors
if sender.error:
    print(f"Configuration error: {sender.error.error}")

# Connect and send frame
error = sender.connect()
if not error:
    frame_bytes = read_frame_data()  # Your frame data
    error = sender.send_frame(
        frame=frame_bytes,
        frame_id=1,
        compress=True,
        auto_batch=True
    )
    if error:
        print(f"Send failed: {error.error}")

sender.close()
```

### Receiver Example

```python
from bbsengine6.net import TCPReceiver

# Listen for frames
receiver = TCPReceiver("127.0.0.1", 4200, timeout=1.0)

if receiver.error:
    print(f"Setup error: {receiver.error.error}")
else:
    frame = receiver.receive()
    if frame:
        print(f"Received frame {frame.frame_id}: {frame.width}x{frame.height}")
        # Process frame.blocks

receiver.close()
```

## UDP Frame Transmission

### Sender Example

```python
from bbsengine6.net import UDPSender

sender = UDPSender("streaming.host", 4200)

frame_data = get_video_frame()
error = sender.send_frame(
    frame=frame_data,
    frame_id=1,
    compress=False,
    auto_batch=True
)

if error:
    print(f"Send error: {error.error}")

sender.close()
```

### Receiver Example (with Callbacks)

```python
from bbsengine6.net import UDPReceiver

def on_frame_received(frame_bytes, frame_id):
    print(f"Frame {frame_id} complete: {len(frame_bytes)} bytes")

def on_idle():
    # Called when no data available
    return True  # Continue listening

receiver = UDPReceiver(
    "127.0.0.1",
    4200,
    frame_received_callback=on_frame_received,
    idle_callback=on_idle,
    blocking=True,
    timeout=0.5
)

if not receiver.error:
    receiver.start_listening()

receiver.close()
```

## Router: Mixed Recipient Routing

### Route Notifications and Frames Together

```python
from bbsengine6.net import InternetRouter

router = InternetRouter(local_machine="myhost")

# Mix notification and frame addresses
addresses = [
    "alice@local",                    # Local notification
    "bob@remote.org",                 # Remote notification
    "tcp://camera:4200/feed",         # TCP frame
    "udp://sensor:4200/data",         # UDP frame
    "invalid@@@address",              # Error
]

local_notif, remote_notif, frames, errors = router.route(addresses)

print(f"Local notifications: {local_notif}")
# → ['alice']

print(f"Remote notifications: {remote_notif}")
# → {'remote.org': ['bob']}

print(f"Frames: {frames}")
# → {'tcp://camera:4200/feed': FrameAddress(...),
#    'udp://sensor:4200/data': FrameAddress(...)}

print(f"Errors: {errors}")
# → {'invalid@@@address': 'Invalid address (frame: ..., notification: ...)'}
```

### Classify Individual Address

```python
router = InternetRouter()

print(router.classify_address("alice@host"))           # 'notification'
print(router.classify_address("tcp://host:4200/"))     # 'frame'
print(router.classify_address("not an address"))       # 'invalid'
```

## Constructor Flexibility

### TCP/UDP: Multiple Calling Patterns

```python
# Old API (positional)
sender = TCPSender("example.com", 4200)

# Old API (kwargs)
sender = TCPSender(host="example.com", port=4200)

# New API (DSN string)
sender = TCPSender("tcp://example.com:4200/")

# New API (DSN kwarg)
sender = TCPSender(dsn="tcp://example.com:4200/")

# New API (FrameAddress object)
from bbsengine6.net import FrameAddressParser
addr = FrameAddressParser.parse("tcp://example.com:4200/")
sender = TCPSender(address=addr.value)
```

### Backward Compatibility

- All old-style constructors continue to work
- No breaking changes to existing code
- New DSN style optional, not required

## Error Handling Pattern

All frame transport operations return `Optional[ParseResult]`:
- `None` on success
- `ParseResult` with error details on failure

```python
error = sender.send_frame(frame_data, frame_id=1)
if error:
    # ParseResult object
    print(f"Error: {error.error}")      # Message
    print(f"Code: {error.code}")        # Code
else:
    # Success
    print("Frame sent successfully")
```

## Configuration Constants

```python
from bbsengine6.net import (
    CHUNK_SIZE,              # 64
    DEFAULT_PORT,            # 4200
    COMPRESSION_ENABLED,     # False
    BUFFER_SIZE,             # 65507
    TCP_BUFFER_SIZE,         # 8192
    UDP_BUFFER_SIZE,         # 65507
    RETRY_DELAY,             # 0.2 seconds
    RETRY_COUNT,             # 5
)
```

## Coexistence: Notifications + Frames

Both systems can operate simultaneously:

```python
from bbsengine6.net import TCPSender, get_integration

# Start frame transmission
frame_sender = TCPSender("tcp://remote:4200/")
frame_sender.connect()
frame_sender.send_frame(frame_data, frame_id=1)

# Also send notifications
notif = get_integration()
result = notif.send(
    notification_type="alert",
    recipients=["alice@host", "bob@remote"],
    template="warning",
    template_vars={"level": "high"}
)

# Both systems work independently
frame_sender.close()
```

## Dependencies

**Imported:**
- Standard library: `socket`, `struct`, `time`, `zlib`, `logging`, `math`, `collections`, `dataclasses`, `enum`, `typing`, `urllib.parse`
- BBSEngine6 internal: `database`, `notify`, `io` modules

**NOT imported:**
- `numpy` (frame data handled as bytes)
- `asimov` (completely independent)

## Summary: Key Features

✅ **Unified addressing**: Frame (DSN) + Notification (SMTP) in one router  
✅ **RFC 3986 compliant**: Standard URI scheme for frames  
✅ **Hybrid query parameters**: Transport handles standard, app handles custom  
✅ **Error results**: No exceptions, all errors as ParseResult objects  
✅ **Constructor overloading**: Multiple API styles supported  
✅ **Zero new dependencies**: Stdlib only (unlike asimov which requires numpy)  
✅ **Backward compatible**: All existing notification code works unchanged  
✅ **Mixed routing**: Handle notifications and frames in same recipient list  
✅ **Fully validated**: Credentials, paths, hosts, ports all sanitized  

## Migration from Asimov

If you're already using asimov's net module:

1. **Asimov continues unchanged**: Keep using asimov.net for your code
2. **BBSEngine6 now has frame support**: Use bbsengine6.net for new frame code
3. **No conflicts**: Both can coexist in same project
4. **Similar API**: BBSEngine6 version is compatible enough

Example migration:
```python
# Old: from asimov.net import TCPSender
# New:
from bbsengine6.net import TCPSender

# Code works the same
sender = TCPSender("host", 4200)
sender.connect()
sender.send_frame(frame, frame_id=1)
```
