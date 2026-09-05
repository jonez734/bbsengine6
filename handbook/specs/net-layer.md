# bbsengine6.net — network layer

> **Status:** canonical. Package renamed from `bbsengine6/internet/`
> to `bbsengine6/net/` (the import path `bbsengine6.net` has always
> been correct). Integration now hooks into
> `bbsengine6.message.store_message`; the deleted notify package is
> gone. **47 tests passing** under `py/tests/test_net_frames/` and
> `py/tests/test_internet*.py` (per the 2026-07-22 audit; the older
> "46 + 1 skipped" snapshot in `NET_LAYER.md` is stale).

The `bbsengine6.net` package adds SMTP-style inter-machine
addressing (`user@machine`), a transport stack (TCP / UDP /
WebSocket), a binary packet system with HMAC authentication, and
the integration layer that routes local recipients through the
unified message system and remote recipients through the WebSocket
server.

## Contents

- [Architecture](#architecture)
- [Public API](#public-api)
- [File layout](#file-layout)
- [Quick start](#quick-start)
- [Database schema](#database-schema)
- [WebSocket protocol](#websocket-protocol)
- [Error handling](#error-handling)
- [Test coverage](#test-coverage)
- [Migration notes](#migration-notes)

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   Application (game package)                  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                  send_with_internet(channel, recipients, …)
                         │
                         ▼
            ┌────────────────────────┐
            │   NotifyIntegration    │   integration.py
            └─────┬──────────┬───────┘
                  │          │
       local users│          │remote by machine
                  ▼          ▼
   ┌─────────────────────┐  ┌───────────────────────────────┐
   │ message.store_      │  │  MachineRegistry.get(name)    │
   │ message_with_checks │  │  → host, port, auth_token     │
   │ (bbsengine6.message)│  │  WebSocketTransport           │
   └─────────────────────┘  │  .send_to_remote_sync(...)    │
                            └───────────────────────────────┘
```

Three address types are detected automatically:

| Type       | Format                | Example                       | Detection                |
|------------|-----------------------|-------------------------------|--------------------------|
| `LOCAL`    | `user@local`          | `alice@local`                 | machine matches `local_machine` (default `"local"`) |
| `REMOTE`   | `user@machine`        | `bob@machine1`                | single-label machine name |
| `FEDERATED`| `user@fqdn`           | `charlie@remote.example.com`  | machine contains a `.` (FQDN) |

## Public API

### High-level

```python
from bbsengine6.net import send_with_internet

result = send_with_internet(
    channel="message_received",
    recipients=["alice@local", "bob@machine1", "carol@remote.example.com"],
    template="User {sender} sent you a message: {body}",
    template_vars={"sender": "alice", "body": "Hello!"},
    sender_moniker="alice",
)
```

Returns:

```python
{
    "local": int | None,                       # message_id from store_message_with_checks (None on failure)
    "local_stored": List[str],                 # monikers stored locally
    "local_blocked": List[str],                # monikers skipped because they blocked the sender
    "remote": Dict[str, Tuple[bool, str]],     # machine → (success, message)
    "errors": Dict[str, str],                  # address or "rate_limit" / "local" → error
    "summary": Tuple[int, int],                # (success_count, failure_count)
}
```

### Address parsing

| Symbol              | Definition                                                                   |
|---------------------|------------------------------------------------------------------------------|
| `AddressType`       | `Enum(LOCAL, REMOTE, FEDERATED)`                                             |
| `InternetAddress`   | `dataclass(user, machine, full_address, address_type)`                       |
| `ParseResult`       | `dataclass(valid: List[InternetAddress], invalid: Dict[str, str])`           |
| `AddressParser`     | `class AddressParser(local_machine: str = "local")`                         |
| `parse_address`     | `(address: str, local_machine: str = "local") -> InternetAddress`            |
| `is_internet_address`| `(address: str, local_machine: str = "local") -> bool`                     |
| `get_parser`        | `(local_machine: str = "local") -> AddressParser`                            |

Validation regex: `^([a-zA-Z0-9._%-]+)@([a-zA-Z0-9.-]+)$`. The user
part accepts alphanumeric, dot, underscore, percent, hyphen; the
machine part accepts alphanumeric, dot, hyphen.

### Routing

| Symbol              | Signature                                                                                                  |
|---------------------|------------------------------------------------------------------------------------------------------------|
| `InternetRouter`    | `class InternetRouter(local_machine: str, registry: MachineRegistry)`                                      |
| `route_recipients`  | `(recipients: List[str], local_machine: str = "local") -> Tuple[List[str], Dict[str, List[str]], Dict[str, str]]` |
| `get_router`        | `(local_machine: str = "local", registry=None) -> InternetRouter`                                          |
| `InternetRouter.resolve_machine` | `(machine: str) -> Tuple[str | None, int | None, str | None]`                            |

### Machine registry

| Symbol              | Definition                                                                   |
|---------------------|------------------------------------------------------------------------------|
| `MachineConfig`     | `dataclass(machine_name, host, port, auth_token=None, tls_enabled=False, verify_cert=True)` with `.ws_url() -> str` |
| `MachineRegistry`   | In-process + DB-backed cache                                                |
| `get_registry`      | `(dbname: str = "bbsengine6") -> MachineRegistry`                            |

`MachineRegistry.register(machine_name, host, port, auth_token=None,
tls_enabled=False, verify_cert=True)` upserts a row into
`postoffice.machine_registry`. `list_all()` returns every registered
machine. `unregister(name)` removes a row. `get(name)` returns the
`MachineConfig` or `None`. `ws_url()` returns
`"wss://host:port/notify"` when TLS is enabled and `"ws://..."`
otherwise.

### WebSocket transport

| Symbol                          | Definition                                                                                       |
|---------------------------------|--------------------------------------------------------------------------------------------------|
| `WebSocketTransport`            | `class` with `send_to_remote_sync(host, port, recipients, message_data, auth_token)` (sync shim over `send_to_remote`) |
| `WebSocketServer`               | `class` registered with `MessageRouter`; per-connection session IDs via `bbsengine6.session.SessionManager.alloc_session_id` |
| `WebSocketProtocol`             | `class` for the server-side receive handler                                                       |
| `ChannelState`                  | Per-server pub/sub state; one instance shared between `WebSocketServer` and `ChannelServiceHandler` |
| `channel_subscribe` / `_unsubscribe` / `_unsubscribe_all` | mutate `ChannelState`                                       |
| `channel_register_callback` / `_unregister_callback` / `_unregister_all_callbacks` | register fanout callbacks                   |
| `channel_get_subscribers` / `channel_get_session_channels` | queries                                                |
| `channel_publish`               | fanout a message to all subscribers of a channel                                                  |

### Packet system

| Symbol                | Definition                                                                            |
|-----------------------|---------------------------------------------------------------------------------------|
| `Packet`              | wire-format envelope with header, payload, checksum, HMAC signature                  |
| `PACKET_TYPE_FILE` / `PACKET_TYPE_MESSAGE` / `PACKET_TYPE_PING` / `PACKET_TYPE_PONG` | int constants                                            |
| `MAX_BLOCK_SIZE` / `MAX_PAYLOAD_SIZE` | block / payload size caps                                                   |
| `CHECKSUM_ALGORITHM` / `CHECKSUM_HEX_LEN` | checksum metadata                                                   |
| `encode_packet` / `decode_packet` | serialize/deserialize                                                   |
| `get_packet_type` / `register_packet_type` | type registry                                                |
| `FilePacket` / `MessagePacket` / `PingPacket` / `PongPacket` | packet subclasses                                  |
| `PacketTypeError` / `PacketDecodeError` / `PacketChecksumError` | exception types                              |
| `CryptoHash` / `PacketAuthError` / `get_crypto` | HMAC primitives                                                |

### Frame addressing

The frame layer is **DSN-style URI** addressing for the asimov
net subsystem. The frame helpers live alongside the rest of the
net package for convenience but are owned by `asimov.net`; import
from `asimov.net` for new code.

| Symbol                          | Definition                                                                   |
|---------------------------------|------------------------------------------------------------------------------|
| `FrameAddress`                  | URI-shaped frame address                                                     |
| `FrameAddressParser`            | parses `FrameAddress` strings                                               |
| `FrameScheme`                   | enum of schemes                                                              |
| `ParseResult`                   | parser result envelope                                                       |
| `Frame` / `NumpyFrame`          | frame value types                                                            |
| `frame_from_any` / `frames_equal` | helpers                                                                    |
| `TCPSender` / `TCPReceiver`     | framed TCP primitives                                                        |

### Integration

| Symbol                  | Definition                                                                                  |
|-------------------------|---------------------------------------------------------------------------------------------|
| `NotifyIntegration`     | `class NotifyIntegration(local_machine="local", message_module=None, registry=None)`        |
| `get_integration`       | `(local_machine="local", message_module=None, registry=None) -> NotifyIntegration`         |
| `send_with_internet`    | module-level convenience (see signature above)                                             |
| `NotifyIntegration.can_send_to` | `(recipients) -> bool`                                                                  |

### Ping helper

The `bbsengine6.net.ping` module exposes a CLI for WebSocket
liveness checks. Imported as `from bbsengine6.net import
ping_send, ping_main, ping_connect, ping_build_parser,
PingUnavailable`.

## File layout

```
py/src/bbsengine6/net/
├── __init__.py            # Public re-exports (see API table)
├── address.py             # AddressType, InternetAddress, AddressParser, parse_address
├── crypto.py              # CryptoHash, PacketAuthError, get_crypto
├── defaultrouter.py       # Default InternetRouter wiring
├── frame_address.py       # FrameAddress, FrameAddressParser, FrameScheme, ParseResult
├── frame_types.py         # Frame, NumpyFrame, frame_from_any, frames_equal
├── integration.py         # NotifyIntegration, send_with_internet
├── packet.py              # Packet, encode_packet, decode_packet, register_packet_type
├── packet_codec.py        # wire codec helpers
├── packet_types.py        # FilePacket, MessagePacket, PingPacket, PongPacket
├── ping.py                # ping CLI + helpers
├── registry.py            # MachineConfig, MachineRegistry, get_registry
├── router.py              # InternetRouter, get_router, route_recipients
├── socket.py              # recv_all, recv_udp, send_with_length, recv_with_length
├── SPEC.md                # in-package spec / changelog
├── tcp.py                 # TCPSender, TCPReceiver
├── transport.py           # WebSocketTransport, WebSocketProtocol, WebSocketServer, ChannelState
└── udp.py                 # UDP helpers
```

## Quick start

```python
from bbsengine6.net import send_with_internet, get_registry

# 1. Register remote machines (one-time)
registry = get_registry()
registry.register(
    machine_name="machine1",
    host="remote.example.com",
    port=8765,
    auth_token="secret123",
    tls_enabled=True,
)

# 2. Send to mixed local/remote recipients
result = send_with_internet(
    channel="alert",
    recipients=[
        "alice@local",                  # local user
        "bob@machine1",                  # remote machine (registered above)
        "carol@remote.example.com",      # federated (no registry entry → falls through to routing error)
    ],
    template="Alert: {message}",
    template_vars={"message": "System maintenance"},
    sender_moniker="system",
)

# 3. Inspect result
local_ok = result["local"] is not None
remote_ok = all(ok for ok, _ in result["remote"].values())
if result["errors"]:
    for addr, err in result["errors"].items():
        print(f"{addr}: {err}")
```

## Database schema

```sql
CREATE TABLE postoffice.machine_registry (
    machine_name TEXT PRIMARY KEY,
    host         TEXT NOT NULL,
    port         INTEGER NOT NULL DEFAULT 8765,
    auth_token   TEXT,
    tls_enabled  BOOLEAN DEFAULT FALSE,
    verify_cert  BOOLEAN DEFAULT TRUE,
    created_at   TIMESTAMP DEFAULT NOW(),
    updated_at   TIMESTAMP DEFAULT NOW()
);
```

`MachineRegistry` caches `MachineConfig` instances per process; the
cache is invalidated on `register()` / `unregister()` so reads after
a write see the new value.

## WebSocket protocol

**Send (client → server):**

```json
{
    "type": "notify",
    "recipients": ["alice", "bob"],
    "data": {
        "type": "message_received",
        "template": "New message",
        "template_vars": {},
        "sender_moniker": "charlie",
        "data": {},
        "urgency": "ROUTINE"
    },
    "auth_token": "optional_token"
}
```

**Response (server → client):**

```json
{ "success": true,  "message": "Notification processed", "delivered": 2 }
{ "success": false, "error": "Invalid recipients list",   "code": "INVALID_PAYLOAD" }
```

The transport layer raises `PacketDecodeError` / `PacketChecksumError`
on a malformed envelope; both are caught at the `WebSocketServer`
boundary so a single bad frame cannot take down the server.

## Error handling

| Failure mode                | Behavior                                                                           |
|-----------------------------|------------------------------------------------------------------------------------|
| Invalid address format      | Collected in `result["errors"][address]` with `"Invalid address format (expected user@machine)"` |
| Missing machine in registry | `result["remote"][machine] = (False, "Machine not configured in registry: <name>")` |
| `bbsengine6.message` missing | `result["local"] = None`, `result["errors"]["all"] = "bbsengine6.message not available"`, `result["summary"] = (0, n)` |
| WebSocket timeout           | `result["remote"][machine] = (False, "WebSocket timeout after 10.0s")`            |
| Rate-limited (local)        | `result["errors"]["rate_limit"] = "Local rate limit exceeded for sender=<m> on channel=<c>"` |

Thread safety: `AddressParser`, `InternetRouter` are stateless
constructors; `MachineRegistry` is locked per cache update;
`WebSocketTransport` wraps async send calls in a sync helper that
runs the asyncio loop to completion.

## Test coverage

47 tests passing (audit snapshot 2026-07-22):

| Module           | Tests | Notes                                                              |
|------------------|-------|--------------------------------------------------------------------|
| `address.py`     | 11    | LOCAL / REMOTE / FEDERATED classification, regex edge cases        |
| `router.py`      | 8     | local/remote grouping, registry resolution                          |
| `transport.py`   | 4     | WebSocket send/ack round-trip                                        |
| `integration.py` | 14    | `NotifyIntegration.send` happy path, rate-limit, blocking, errors  |
| `registry.py`    | 10    | `register` / `unregister` / `get` / `list_all` / `ws_url`            |

Run:

```bash
pytest py/src/bbsengine6/tests/test_internet*.py -v
pytest py/src/bbsengine6/tests/test_net_frames/ -v
```

## Migration notes

**Package rename.** Older revisions of `bbsengine6/NET_LAYER_INDEX.md`
and `bbsengine6/FEATURES_NET_LAYER.md` showed the package at
`bbsengine6/internet/`. The live path is `bbsengine6/net/` — the
import path `bbsengine6.net` has always been correct; the on-disk
directory was renamed at some point during the Phase 2/3 work.

**Deleted subsystem hook.** `NotifyIntegration.send` and the rest of
`integration.py` previously called `self.notify_module.send(...)`
against the deleted `bbsengine6.notify` package. Since Phase 7
(2026-07-22) and Phase 10 (2026-08-04), the call is
`self.message_module.store_message_with_checks(...)` followed by
`bbsengine6.message.service.record_message_sent(...)`. There is no
`notify_module` parameter; the parameter is named `message_module`
and the default behavior is to import `bbsengine6.message`
automatically.

**Phase 11 (2026-09-01).** `bbsengine6.message.store_message` is
unchanged at the package surface. Internally it delegates to
`bbsengine6.message.service.store_message`, which delegates to
`bbsengine6.message.dal.messages.store_message_with_recipients`.
The integration layer at `py/src/bbsengine6/net/integration.py`
needs no change.
