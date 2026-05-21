# BBSEngine6 Net Module Specification

## Overview

The `bbsengine6.net` module provides networking infrastructure for BBSEngine6:
- **Notification delivery**: SMTP-like inter-machine notifications using WebSocket
- **Hybrid routing**: Route notifications and frame addresses together
- **Machine registry**: Manage remote machine configurations
- **Integration layer**: Connect with notification system

**Note**: Video frame transmission code has been moved to `asimov.net`. This module focuses on notification infrastructure and hybrid routing capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
└─────────────────────────────────────────────────────────┘
          │                                      │
          ↓                                      ↓
┌──────────────────────────┐     ┌──────────────────────────┐
│  Notification System     │     │  Frame Transmission      │
│  (SMTP-like addressing)  │     │  (in asimov.net)         │
└──────────────────────────┘     └──────────────────────────┘
          │                                      │
          ├─→ AddressParser (user@machine)      │
          ├─→ InternetRouter                    ├─→ from asimov.net import
          ├─→ MachineRegistry                   │   FrameAddressParser,
          └─→ WebSocketTransport                │   TCPSender, UDPSender
                                                │
                                    (asimov handles all frame code)
                                                │
                                    ├─→ FrameAddress
                                    ├─→ Frame, NumpyFrame
                                    └─→ TCP/UDP transports

┌─────────────────────────────────────────────────────────┐
│         Network Layer (TCP/UDP/WebSocket)               │
│         (Frame code in asimov, Notification in bbsengine6)  │
└─────────────────────────────────────────────────────────┘
```

## Module Organization

### Addressing Layer
- **address.py**: SMTP-like notification addressing
  - Supports: `user@machine` format
  - Distinguishes local, remote, and federated addresses
  - `AddressParser`, `InternetAddress`, `AddressType`

### Transport Layer
- **transport.py**: WebSocket transport for notifications
  - `WebSocketTransport`: Async/sync WebSocket client
  - `WebSocketProtocol`: Handle incoming WebSocket notifications

### Service Layer
- **router.py**: Route mixed recipient types
  - `InternetRouter`: Classify and route notifications and frame addresses
  - Automatically detects notification vs frame addresses
  - Uses `asimov.net.FrameAddressParser` for frame addressing

- **registry.py**: Machine registry for remote machine configs
  - `MachineRegistry`: PostgreSQL-backed registry
  - `MachineConfig`: Configuration for remote machines
  - Stores machine endpoints and capabilities

- **integration.py**: Notification system integration
  - `NotifyIntegration`: Unified interface for local + remote notifications
  - Handles routing and delivery to appropriate transport
  - Works with both local bbsengine6.notify and remote machines

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
from bbsengine6.net import AddressParser

parser = AddressParser("local.machine")
address = parser.parse("alice@remote.org")

# address.is_local() → False
# address.is_remote() → True
# address.is_federated() → True
```

## Frame Addressing (DSN Format - from asimov)

Frame addresses follow RFC 3986 URI syntax and are handled by `asimov.net`:

```
scheme://[user[:password]@]host[:port][/path][?query]
```

### Supported Schemes (from asimov.net)

| Scheme | Transport | Default Port | Use Case |
|--------|-----------|---|---|
| `tcp://` | TCP Socket | 5000 | Reliable, ordered delivery |
| `udp://` | UDP Socket | 5000 | Fast, stateless delivery |
| `unix://` | Unix Domain Socket | N/A | Local IPC |
| `ws://` | WebSocket | 80 | HTTP-compatible unencrypted |
| `wss://` | WebSocket Secure | 443 | HTTP-compatible encrypted |

### Examples

```
tcp://camera.local/
tcp://alice:secret@remote.host:5000/
udp://224.1.1.1:5000/
unix:///var/run/frame.sock
ws://stream.example.com/camera/1/hires?quality=high
wss://secure.example.com:443/frames
```

**To use frame addressing:**
```python
from asimov.net import FrameAddressParser, TCPSender

parser = FrameAddressParser()
result = parser.parse("tcp://camera:5000/")

if result.success:
    sender = TCPSender(address=result.value)
    sender.connect()
    sender.send_frame(frame_data, frame_id=1)
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
    "tcp://camera:5000/feed",         # TCP frame (routed via asimov)
    "udp://sensor:5000/data",         # UDP frame (routed via asimov)
    "invalid@@@address",              # Error
]

local_notif, remote_notif, frames, errors = router.route(addresses)

print(f"Local notifications: {local_notif}")
# → ['alice']

print(f"Remote notifications: {remote_notif}")
# → {'remote.org': ['bob']}

print(f"Frames: {frames}")
# → {'tcp://camera:5000/feed': FrameAddress(...),
#    'udp://sensor:5000/data': FrameAddress(...)}

print(f"Errors: {errors}")
# → {'invalid@@@address': 'Invalid address ...'}
```

**Key Features:**
- ✓ Detects frame addresses (tcp://, udp://, etc.)
- ✓ Detects notification addresses (user@machine)
- ✓ Returns frame addresses from `asimov.net` parser
- ✓ Separates local vs remote recipients
- ✓ Captures invalid addresses with error messages

## Notification Integration

### Send Notifications

```python
from bbsengine6.net import get_integration

notif = get_integration()

# Send to mixed recipients (some local, some remote)
result = notif.send(
    notification_type="alert",
    recipients=[
        "alice@local",              # Local via bbsengine6.notify
        "bob@remote.org",           # Remote via WebSocket
    ],
    template="warning",
    template_vars={"level": "high", "source": "camera"}
)

# Result contains routing info
print(f"Local delivery: {result['local']}")
print(f"Remote delivery: {result['remote']}")
```

### Check Delivery Capability

```python
notif = get_integration()

# Check if we can send to specific recipients
can_send = notif.can_send_to(["alice@local", "bob@remote"])
# → True if notify module available, False otherwise
```

## Machine Registry

### Configure Remote Machines

```python
from bbsengine6.net import MachineRegistry, MachineConfig

registry = get_registry()

# Add remote machine configuration
config = MachineConfig(
    name="remote-server",
    host="remote.example.com",
    port=5000,
    protocol="tcp",
    credentials={"token": "xyz123"},
)

registry.add_machine(config)

# Look up machine for routing
machine = registry.get_machine("remote.example.com")
```

## Coexistence: Notifications + Frames

Both systems can operate simultaneously:

```python
from asimov.net import TCPSender
from bbsengine6.net import get_integration

# Start frame transmission (asimov)
frame_sender = TCPSender("tcp://remote:5000/")
frame_sender.connect()
frame_sender.send_frame(frame_data, frame_id=1)

# Also send notifications (bbsengine6)
notif = get_integration()
result = notif.send(
    notification_type="alert",
    recipients=["alice@host", "bob@remote"],
    template="warning",
)

# Both systems work independently
frame_sender.close()
```

## Dependencies

**Imported:**
- Standard library: `socket`, `struct`, `time`, `logging`, `dataclasses`, `enum`, `typing`, `urllib.parse`
- BBSEngine6 internal: `database`, `notify`, `io` modules
- Asimov external: `asimov.net` (for frame addressing)

**NOT imported:**
- `numpy` (frame data is handled by asimov)
- `asimov` core (only uses asimov.net for frame code)

## Code Organization

```
bbsengine6/net/
├── __init__.py           # 16 exports (notification + routing)
├── address.py            # SMTP-like address parsing
├── router.py             # Hybrid routing (notifications + frames)
├── registry.py           # Machine registry with PostgreSQL
├── integration.py        # Notification system integration
└── transport.py          # WebSocket transport
```

## Summary: Key Features

✅ **SMTP-like notification addressing**: `user@machine` format  
✅ **Hybrid routing**: Handle notifications and frame addresses together  
✅ **Frame support via asimov**: Import from `asimov.net` for frames  
✅ **Machine registry**: PostgreSQL-backed remote machine configuration  
✅ **WebSocket transport**: Secure notification delivery  
✅ **Integration layer**: Connect with local and remote notification systems  
✅ **Independence from asimov core**: Only uses asimov.net, not asimov  
✅ **Error handling**: No exceptions, all errors as result objects  

## Migration from Previous bbsengine6.net

If you were using frame code from bbsengine6.net:

**Old way (no longer available):**
```python
# from bbsengine6.net import TCPSender, Frame, FrameAddress
# ✗ These are no longer in bbsengine6.net
```

**New way (use asimov.net):**
```python
from asimov.net import TCPSender, Frame, FrameAddress

sender = TCPSender("tcp://host:5000/")
sender.connect()
sender.send_frame(frame_data, frame_id=1)
```

**For routing (bbsengine6 still handles):**
```python
from bbsengine6.net import InternetRouter

router = InternetRouter()
local, remote, frames, errors = router.route([
    "alice@local",           # Notification
    "tcp://camera:5000/",    # Frame (router parses via asimov)
])
```

## Architecture Benefits

This separation provides:
- **Clear responsibility**: asimov owns frame transmission, bbsengine6 owns notifications
- **No duplication**: Frame code lives in one place
- **Independent evolution**: Each project can evolve separately
- **Hybrid capabilities**: Router can work with both systems
- **No circular dependencies**: bbsengine6 only uses asimov.net (not core asimov)

## Packet System

The `bbsengine6.net` packet system provides a unified, extensible protocol for transmitting Files and Messages over WebSocket or other transports.

### Overview

**Three core capabilities:**
- **File transmission**: Large files split into 1MB blocks with checksums
- **Message transmission**: RFC 822-aligned messages with sender, subject, and content
- **Custom packet types**: Extensible registry for adding new packet types

**Key features:**
- SHA256 checksums for integrity verification (always computed)
- Optional zlib compression per-packet
- Block-based transmission for large files
- ASCII-only strings for security
- Path traversal protection for filenames

### Packet Architecture

#### Header Structure

All packets follow a binary header-body structure:
```
[fixed-size binary header] + [variable payload] + [checksum]
```

**Common header fields (all packets):**
- `packet_type` (1 byte): identifies packet type (FILE=10, MESSAGE=11)
- `timestamp` (8 bytes): seconds since epoch (float64)
- `packet_id` (4 bytes): unique packet identifier
- `checksum_len` (2 bytes): always 64 for SHA256 hex

**Payload verification:**
All packet payloads are verified with SHA256 checksums. On decode, if the checksum doesn't match, a `PacketChecksumError` is raised.

#### Block System

**FilePacket uses blocks for large files:**
- Each FilePacket contains 1 block (due to < 1MB payload limit)
- For a 100MB file: sender creates 100 FilePackets with different `block_id`
- Receiver reassembles by ordering blocks by `block_id`
- Blocks can be individually compressed

**MessagePacket stores content as single field** (no block splitting, kept simple)

### FilePacket Specification

**Binary header format:** `!BdIHQHIIBBHH` (46 bytes)

```
B  = packet_type (10)
d  = timestamp (seconds since epoch)
I  = packet_id (unique identifier)
H  = filename_len (1-256 bytes)
Q  = file_size (total file size in bytes)
H  = mime_type_len (1-256 bytes)
I  = total_blocks (how many blocks total)
I  = block_id (which block this is, 0-indexed)
B  = compressed (0 or 1)
B  = has_block_sizes (0 or 1, for variable-size blocks)
H  = blocks_in_packet (usually 1)
H  = checksum_len (always 64)
```

**Payload layout:**
```
[filename in ASCII][mime_type in ASCII][block_sizes if present]
[block data][SHA256 checksum as 64-char hex string]
```

**Example: Sending a 5MB file**
```python
from bbsengine6.net import FilePacket, encode_packet

# File to send: document.pdf (5,242,880 bytes)
# Split into 5 blocks of 1MB each

for block_id in range(5):
    # Read 1MB chunk
    block_data = file_data[block_id * 1048576 : (block_id + 1) * 1048576]
    
    packet = FilePacket(
        filename="document.pdf",
        file_size=5242880,           # Total file size
        mime_type="application/pdf",
        total_blocks=5,              # Total blocks for this file
        block_id=block_id,           # Current block (0-4)
        blocks=[block_data],
        compressed=False,
    )
    
    # Encode and send
    encoded = encode_packet(packet)
    transport.send_packet_sync(host, port, packet)

# Receiver assembles blocks in order by block_id
```

**Validation on decode:**
- `filename_len`: 1-256 bytes, ASCII only
- `mime_type_len`: 1-256 bytes, ASCII only
- `file_size` > 0
- `total_blocks` > 0
- `block_id` < `total_blocks`
- No path traversal in filename (`../`, `/`, `\`)
- Checksum mismatch raises `PacketChecksumError`

### MessagePacket Specification

**Binary header format:** `!BdIHHHIBH` (30 bytes)

```
B  = packet_type (11)
d  = timestamp (seconds since epoch)
I  = packet_id (unique identifier)
H  = sender_len (1-256 bytes)
H  = subject_len (0-256 bytes, can be empty)
H  = content_type_len (1-256 bytes)
I  = content_len (up to 1,048,575 bytes)
B  = compressed (0 or 1)
H  = checksum_len (always 64)
```

**Payload layout:**
```
[sender in ASCII][subject in ASCII][content_type in ASCII]
[raw content bytes][SHA256 checksum as 64-char hex string]
```

**RFC 822 Alignment:**

MessagePacket fields map directly to RFC 822 email headers:

| MessagePacket | RFC 822 |
|---|---|
| `sender` | `From:` |
| `subject` | `Subject:` |
| `content_type` | `Content-Type:` |
| `timestamp` | `Date:` (implicit) |
| `content` | Message body |

**Example: RFC 822 message construction**
```python
from datetime import datetime
from email.utils import formatdate

packet = MessagePacket(
    sender="alice@example.com",
    subject="Hello Bob",
    content_type="text/plain; charset=utf-8",
    content=b"This is the message body.",
)

# Construct RFC 822 format
rfc822_msg = (
    f"From: {packet.sender}\n"
    f"Subject: {packet.subject}\n"
    f"Date: {formatdate(packet.timestamp)}\n"
    f"Content-Type: {packet.content_type}\n"
    f"\n"
    f"{packet.content.decode('utf-8')}"
)
```

**Example: Sending a message**
```python
from bbsengine6.net import MessagePacket, encode_packet

packet = MessagePacket(
    sender="alice",
    subject="Meeting tomorrow at 2pm",
    content_type="text/plain",
    content=b"Don't forget about the team meeting.",
)

encoded = encode_packet(packet)
transport.send_packet_sync(host, port, packet)
```

**Validation on decode:**
- `sender_len`: 1-256 bytes, ASCII only
- `subject_len`: 0-256 bytes, ASCII only (can be empty)
- `content_type_len`: 1-256 bytes, ASCII only
- `content_len` < 1,048,576 bytes
- Checksum mismatch raises `PacketChecksumError`

### Compression

**How it works:**
- Optional per-packet via `compressed` flag
- Uses zlib compression (level 6)
- For FilePacket: compresses individual blocks
- For MessagePacket: compresses content

**Benefits:**
- Video-like data: 10x compression typical
- Text data: 3-5x compression typical
- Binary files: varies (PDFs, images may not compress well)

**Example: Compressed FilePacket**
```python
packet = FilePacket(
    filename="data.csv",
    file_size=100000,
    mime_type="text/csv",
    total_blocks=1,
    block_id=0,
    blocks=[csv_data],  # 100KB CSV
    compressed=True,    # Enable compression
)

encoded = encode_packet(packet)
# Payload typically reduced to 20-30KB due to compression
```

On decode, compressed blocks are automatically decompressed.

### Checksums & Integrity

**SHA256 always computed:**
- All payloads have SHA256 checksums
- Checksum computed before encoding
- Stored as 64-character hex ASCII string
- Verified on decode (constant-time comparison)

**Checksum verification:**
```python
from bbsengine6.net import decode_packet, PacketChecksumError

try:
    packet = decode_packet(binary_data)
except PacketChecksumError:
    print("Packet corrupted in transit")
    # Discard packet, request retransmission
```

### Security Considerations

#### Input Validation

**FilePacket filename:**
- ASCII only (no UTF-8)
- No path traversal characters: `../`, `/`, `\`
- No null bytes
- Max 256 bytes

**All string fields:**
- ASCII encoding enforced
- Lengths validated against header values
- Null bytes rejected

**Block sizes:**
- Individual blocks ≤ 1 MB
- Total payload per packet < 1 MB
- Block count validated (blocks_in_packet vs. declared sizes)

#### Transmission Security

**Checksums prevent corruption:**
- Silent corruption detected and rejected
- Malformed packets explicitly rejected with PacketDecodeError

**No trust assumptions:**
- Assume all input from network is potentially malicious
- All decode operations perform bounds checking
- Struct unpacking errors caught and converted to PacketDecodeError

### Error Handling

**Exception hierarchy:**
- `PacketTypeError`: Unknown packet type (extends ValueError)
- `PacketDecodeError`: Malformed packet data (extends ValueError)
- `PacketChecksumError`: Checksum verification failed (extends ValueError)

**Example error handling:**
```python
from bbsengine6.net import (
    decode_packet,
    PacketTypeError,
    PacketDecodeError,
    PacketChecksumError,
)

try:
    packet = decode_packet(raw_bytes)
except PacketChecksumError:
    print("Packet corrupted")
except PacketDecodeError as e:
    print(f"Malformed packet: {e}")
except PacketTypeError:
    print("Unknown packet type")
```

### Extensibility: Custom Packet Types

The packet system supports custom types via a type registry.

**Creating a custom packet type:**
```python
from dataclasses import dataclass, field
from bbsengine6.net import Packet, register_packet_type
from bbsengine6.net.packet_codec import compute_checksum, verify_checksum
import struct

PACKET_TYPE_IMAGE = 20

@register_packet_type
@dataclass
class ImagePacket(Packet):
    """Custom packet for transmitting images."""
    width: int = 0
    height: int = 0
    format: str = "RGB"  # RGB, RGBA, etc.
    packet_type: int = field(init=False, default=PACKET_TYPE_IMAGE)

    @staticmethod
    def encode(packet: "ImagePacket") -> bytes:
        """Encode ImagePacket to binary."""
        # Your encoding logic
        pass

    @staticmethod
    def decode(data: bytes) -> "ImagePacket":
        """Decode binary to ImagePacket."""
        # Your decoding logic
        pass

# Now you can use it
from bbsengine6.net import encode_packet, decode_packet

img = ImagePacket(width=1024, height=768, blocks=[image_data])
encoded = encode_packet(img)
decoded = decode_packet(encoded)
```

**Registry requirements:**
- Class must have `packet_type` attribute (unique int)
- Must have `encode(packet)` static method returning bytes
- Must have `decode(data)` static method returning packet instance
- Decorate with `@register_packet_type`

### Usage Examples

#### Example 1: Send a text file

```python
from bbsengine6.net import FilePacket, WebSocketTransport

# Read file
with open("readme.txt", "rb") as f:
    content = f.read()

# Create packet
packet = FilePacket(
    filename="readme.txt",
    file_size=len(content),
    mime_type="text/plain",
    total_blocks=1,
    block_id=0,
    blocks=[content],
)

# Send
transport = WebSocketTransport()
success, msg = transport.send_packet_sync("example.com", 8000, packet)
print(msg)
```

#### Example 2: Receive and verify a message

```python
from bbsengine6.net import decode_packet, PacketChecksumError

# Receive binary packet from WebSocket
received_bytes = ws.recv()

try:
    packet = decode_packet(received_bytes)
    print(f"From: {packet.sender}")
    print(f"Subject: {packet.subject}")
    print(f"Content-Type: {packet.content_type}")
    print(f"Body: {packet.content.decode('utf-8')}")
except PacketChecksumError:
    print("Message corrupted in transit!")
```

#### Example 3: Stream large file in blocks

```python
from bbsengine6.net import FilePacket, encode_packet

filename = "large_video.mp4"
filesize = 1_000_000_000  # 1 GB
block_size = 1_048_576   # 1 MB

# Calculate blocks
total_blocks = (filesize + block_size - 1) // block_size

with open(filename, "rb") as f:
    for block_id in range(total_blocks):
        block_data = f.read(block_size)
        
        packet = FilePacket(
            filename=filename,
            file_size=filesize,
            mime_type="video/mp4",
            total_blocks=total_blocks,
            block_id=block_id,
            blocks=[block_data],
            compressed=False,  # Video already compressed
        )
        
        encoded = encode_packet(packet)
        transport.send_packet_sync("server.com", 8000, packet)
        print(f"Sent block {block_id + 1}/{total_blocks}")
```

### Constants

```python
from bbsengine6.net import (
    PACKET_TYPE_FILE,           # 10
    PACKET_TYPE_MESSAGE,        # 11
    MAX_BLOCK_SIZE,             # 1,048,576 (1 MB)
    MAX_PAYLOAD_SIZE,           # 1,048,576 (1 MB per packet)
    CHECKSUM_ALGORITHM,         # "sha256"
    CHECKSUM_HEX_LEN,           # 64
)
```

### Performance Notes

- **FilePacket**: Efficient for large files via block streaming
- **MessagePacket**: Optimized for typical email-like messages
- **Compression**: Reduces payload 3-10x depending on content
- **Checksums**: Minimal overhead (SHA256 is fast)
- **Binary format**: No JSON/text overhead, compact binary encoding
