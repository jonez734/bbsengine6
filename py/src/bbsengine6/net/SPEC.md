# bbsengine6.net Specification

## Overview

Network layer for BBSEngine6: SMTP-like addressing, packet system, WebSocket transport, and notification integration.

**Note**: Frame/video transmission code has been moved to asimov.net. This module focuses on notification infrastructure.

## Architecture

```
┌─────────────────────────────────────────┐
│           Application Layer             │
└─────────────────────────────────────────┘
                    │
    ┌───────────────┴───────────────┐
    │                               │
    ▼                               ▼
┌─────────────────────┐   ┌─────────────────────┐
│ Notification System │   │  Frame Transmission │
│ (SMTP-like)         │   │  (asimov.net)       │
└─────────────────────┘   └─────────────────────┘
    │
    ├─→ AddressParser
    ├─→ InternetRouter
    ├─→ MachineRegistry
    └─→ WebSocketTransport

┌─────────────────────────────────────────┐
│    Network Layer (TCP/WebSocket)        │
└─────────────────────────────────────────┘
```

## Components

### Addressing (address.py)

SMTP-like addressing for notifications: `user@machine`, `user@machine:port`

- `AddressParser` - Parse and route addresses
- `InternetAddress` - Parsed address object
- `AddressType` - Enum (LOCAL, REMOTE, FEDERATED)
- `is_internet_address()` - Validate address format
- `parse_address()` - Parse address string

### Packet System

Binary packets for network communication:

- `Packet` - Base packet class
- `FilePacket` - File transfer
- `MessagePacket` - Text messages
- `PingPacket` / `PongPacket` - Keep-alive/latency

Packet format: `[type:1][checksum:8][length:4][payload:n]`

- `encode_packet()` / `decode_packet()` - Serialize/deserialize
- `get_packet_type()` - Get packet type from data
- `register_packet_type()` - Register custom types

### Routing (router.py)

Route notifications to local and remote recipients:

- `InternetRouter` - Route addresses to local/remote
- `get_router()` - Get default router
- `route_recipients()` - Convenience function

Returns: `(local_recipients, remote_by_machine, frame_addresses, errors)`

**Frame support**: Import from asimov.net when needed:
```python
from asimov.net import FrameAddress, FrameAddressParser
```

### Machine Registry (registry.py)

Manage remote machine configurations:

- `MachineRegistry` - Registry of machines
- `MachineConfig` - Per-machine settings
- `get_registry()` - Get default registry

### WebSocket Transport (transport.py)

WebSocket server with service registry:

- `WebSocketServer` - Async WebSocket server
- `WebSocketTransport` - Transport layer
- Services register via `@server.handler(name)` decorator

### HMAC Authentication (crypto.py)

- `CryptoHash` - HMAC-SHA256
- `get_crypto()` - Get instance
- `PacketAuthError` - Auth failure

### Integration (integration.py)

Notification delivery:

- `NotifyIntegration` - Local notifications
- `get_integration()` - Get instance
- `send_with_internet()` - Send via internet

## Usage

```python
from bbsengine6.net import (
    AddressParser,
    InternetRouter,
    Packet,
    WebSocketServer,
    get_router,
    get_registry,
)

# Parse addresses
parser = AddressParser("local")
result = parser.parse("user@machine")
print(f"Type: {result.type}, User: {result.user}, Machine: {result.machine}")

# Route recipients
router = get_router()
local, remote, frames, errors = router.route(["alice@remote", "bob"])

# Create packet
from bbsengine6.net import MessagePacket
packet = MessagePacket(body="Hello!")
data = encode_packet(packet)

# WebSocket server
server = WebSocketServer(host="0.0.0.0", port=8765)

@server.handler("ping")
async def ping(ws, msg):
    await ws.send('{"type":"pong"}')

await server.start()
```

## Constants

```python
# Packet types
PACKET_TYPE_FILE = 1
PACKET_TYPE_MESSAGE = 2
PACKET_TYPE_PING = 3
PACKET_TYPE_PONG = 4

# Limits
MAX_PAYLOAD_SIZE = 65535
MAX_BLOCK_SIZE = 8192
CHECKSUM_HEX_LEN = 64
```

## Dependencies

- `websockets` - WebSocket server/client
- `psycopg` - Database (via bbsengine6.database)

## Imports from asimov.net

When frame support is needed:

```python
from asimov.net import (
    FrameAddress,
    FrameAddressParser,
    Frame,
    NumpyFrame,
    TCPSender,
    TCPReceiver,
    FramePacket,
)
```
