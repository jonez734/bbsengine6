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

#### Channel Pub/Sub

In-process pub/sub fan-out keyed by channel name (e.g.
`member:alice`, `casino:table:blackjack-1`, `system:shout`).
State is held in `ChannelState` and shared between the server and
any `ChannelServiceHandler` so that subscribers registered via the
handler and publishers calling `server.publish(...)` see the same
data.

- `ChannelState` - Bidirectional index: `channel -> {session_id}`
  and `session_id -> {channel}`.
- `channel_subscribe(state, session_id, channel)` / `channel_unsubscribe(...)`
  - Manage subscriptions. `channel_unsubscribe_all(state, session_id)`
  removes a session from every channel.
- `channel_register_callback(state, channel, callback)` - Register
  an in-process callback. Re-registering the same callable is a
  no-op (dedup by identity). Use `channel_unregister_callback(...)`
  or `channel_unregister_all_callbacks(...)` to remove.
- `channel_publish(state, channel, message, server=None,
  sender_moniker=None, args=None)` - Fan out to subscribers. When
  `sender_moniker` and `args` are provided, the publish consults
  `ChannelService.can_publish` (announce-only ACL). Fail-closed on
  errors.

#### Server Lifecycle

`WebSocketServer.on_connect` allocates a monotonic session id via
`SessionManager.alloc_session_id()` and stashes it on the websocket
as `_bbsengine6_session_id`. Service handlers should read this via
`getattr(websocket, "_bbsengine6_session_id", id(websocket))` to
avoid Python id-reuse after GC. On disconnect, the server calls
`router.unregister_session(session_id)` if a router was registered
via `server.register_router(router)`.

#### Constructor

```python
WebSocketServer(
    host="0.0.0.0",
    port=8765,
    handler=None,                    # legacy single-handler API
    secret_key=None,                 # HMAC auth
    channel_state=None,              # shared ChannelState
    session_manager=None,            # shared SessionManager
)
```

When `channel_state` is provided, the server uses it for pub/sub.
Otherwise it creates its own (and subscribers registered through
handlers will not be reachable by `server.publish(...)`). BED
creates a single `ChannelState` and passes it to both the server
and the router.

#### Real-Network Send

`WebSocketTransport.send_to_remote(...)` opens a real
`websockets.connect()` session, sends the JSON payload, and reads
at most one frame as an ack. Returns `(success, message)`. Handles
timeouts via `asyncio.timeout`, refuses connection, and any
`WebSocketException` gracefully.

#### Ping Helper (ping.py)

A small shared helper for the `*-ping` bin scripts
(`bedping`, `bbsengine6-ping`, `casino-ping`, `zoid6-ping`).
The motivation is to give every consumer that opens a
WebSocket to a bbsengine6-based daemon the same friendly
"connection refused" / "host unreachable" / "timed out"
rendering so a stopped daemon produces a one-line operator
message via `bbsengine6.io.echo(level="error")` and a non-zero
exit status — never a Python traceback.

The module exposes:

* `class PingUnavailable(host, port, exc, *, prog="ping")`
  — carries the configured endpoint and the original
  exception. Renders as
  `"<prog>: cannot connect to ws://{host}:{port}/ (is the
  bed daemon running?): {exc}"`. The `prog` keyword is
  keyword-only so the four-arg call site cannot accidentally
  pass the prog in the exc slot.
* `async def connect(host, port, *, path="/", timeout=5.0,
  prog="ping")` — wraps `websockets.connect()` in a
  `asyncio.wait_for(...)` and converts
  `ConnectionRefusedError`, `OSError`,
  `asyncio.TimeoutError`, and `WebSocketException` into
  `PingUnavailable` (chained via `raise ... from exc`). On
  success, returns the live websockets protocol object.
* `async def send_ping(host, port, *, path="/",
  timeout=5.0, prog="ping")` — opens via `connect`,
  sends `{"type":"ping"}`, reads one reply with the same
  timeout, and returns the parsed JSON dict.
* `def build_parser(prog)` — argparse builder shared by
  every consumer shim so `--host`, `--port`, `--path`,
  `--timeout` behave identically regardless of which
  project owns the entry point. `prog` flows into
  `argparse.ArgumentParser(prog=...)` so `--help` shows
  the correct program name.
* `def main(argv, *, prog)` — CLI entry point. Catches
  `PingUnavailable`, calls
  `bbsengine6.io.echo(level="error")`, returns `1` so the
  shim exits non-zero.

Consumers:

* `bbsengine6/bin/bbsengine6-ping` — generic shim
  (`prog="bbsengine6-ping"`).
* `bed/bin/bedping` (existing) and `bed.tools.ping` —
  the bed ping/auth round-trip uses `connect(host, port,
  prog="bedping")` so the friendly error renders with the
  `bedping:` prefix.
* `casino/bin/casino-ping` and `casino.client.CasinoClient.connect`
  — the casino client routes `websockets.connect()` through
  `bbsengine6.net.ping.connect(host, port, path=path,
  prog="casino")` so `ConnectionRefusedError` etc. surface
  as `PingUnavailable` and `CasinoClient.connect` renders
  them via `io.echo(level="error")`.
* `zoid6/bin/zoid6-ping` — zoid6 wraps the bed daemon
  (`prog="zoid6-ping"`).

`PingUnavailable` is re-exported by `bed.tools.ping` so the
existing `bedping` shim continues to work; class identity is
preserved (`bed.tools.ping.PingUnavailable is
bbsengine6.net.ping.PingUnavailable`) for tests that import
from either location.

### HMAC Authentication (crypto.py)

- `CryptoHash` - HMAC-SHA256
- `get_crypto()` - Get instance
- `PacketAuthError` - Auth failure

### Integration (integration.py)

Notification delivery:

- `NotifyIntegration` - Local notifications
- `get_integration()` - Get instance
- `send_with_internet(channel, recipients, template, ...)` - Send
  via internet. The first parameter is `channel` (renamed from
  `notification_type`); it is forwarded to
  `NotifyIntegration.send` as its `channel` argument.

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

## BED Daemon (the consumer of this layer)

The actual bbsengine6 daemon that consumes this net layer is
`py/src/bbsengine6/bed.py` (BED = "BBS Engine Daemon"). It is
a generic WebSocket server that loads a router module via
`--router`, constructs a single shared `ChannelState`, and
hands it to both the server (`WebSocketServer.channel_state`)
and the router (`MessageRouter(channel_state=, server=)`).
This is what makes `server.publish(channel, ...)` and
`router.register_callback(channel, ...)` share the same
fan-out data.

```bash
# Default router (DefaultRouter from bbsengine6.net.defaultrouter)
python -m bbsengine6.bed --host 0.0.0.0 --port 8765

# Custom router
python -m bbsengine6.bed --router casino.zoidnet.MessageRouter
```

**Note on the older `BBSENGINE6_NOTIFYD_*.md` specs in
`handbook/specs/`:** those 10 files describe a separate
"notifyd" daemon that was never built (it depended on
`bbsengine6.notify`, which was deleted in Phase 7 of
`TODO-message-migration.md` in 2026-07-22). BED is the
*only* bbsengine6 daemon that exists in the codebase. The
"notifyd" docs are preserved for historical reference and
are marked SUPERSEDED.
