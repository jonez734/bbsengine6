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
