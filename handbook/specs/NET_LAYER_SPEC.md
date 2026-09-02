# Internet Layer Specification

**Module**: `bbsengine6.net`  
**Status**: Stable (Phase 3 Complete)  
**Test Coverage**: 47 tests, 100% passing  
**Code Quality**: All checks pass (ruff, type hints, linting)

> **STATUS (2026-07-22):** Two stale references in this spec were
> fixed in this revision:
>
> 1. Section 2.1 "Module Structure" showed the package at
>    `bbsengine6/internet/`. The **live** package is at
>    `bbsengine6/net/` (the import path `bbsengine6.net` has
>    always been correct).
> 2. The integration layer in section 2.2 ("Processing
>    Pipeline") and elsewhere refers to `bbsengine6.notify`.
>    The `notify` package was deleted in Phase 7 of
>    `TODO-message-migration.md`; the live integration is
>    `bbsengine6.message.store_message(...)` via
>    `NotifyIntegration` in `py/src/bbsengine6/net/integration.py`.

## 1. Overview

The Internet Layer provides SMTP-like inter-machine messaging for bbsengine6. It extends the existing notification system (`bbsengine6.message`, previously `bbsengine6.notify` before the Phase 7 deletion) to support addressing users across multiple machines using a familiar `user@machine` format.

### 1.1 Problem Statement

Previously, the notification system was local-only, working within a single machine. The Internet Layer solves the need to send notifications between:
- Users on the local machine
- Users on remote machines (same domain)
- Users on federated machines (external domains)

### 1.2 Design Goals

1. **Simple & Elegant**: SMTP-style addressing, minimal API surface
2. **Twisted Architecture**: Clean separation of concerns
3. **Backward Compatible**: Works alongside existing notify system
4. **Graceful Degradation**: Functions with or without remote machines
5. **Extensible**: Foundation for future federation and routing enhancements

## 2. Architecture

### 2.1 Module Structure

```
bbsengine6/net/                       # live path (was `bbsengine6/internet/` in older revisions)
├── __init__.py           # Public API exports
├── address.py            # Address parsing and classification
├── router.py             # Routing logic with registry integration
├── transport.py          # WebSocket protocol (async/sync)
├── integration.py        # Integration with bbsengine6.message (was bbsengine6.notify)
└── registry.py           # Machine configuration management
```

### 2.2 Processing Pipeline

```
Application
    ↓
send_with_internet(recipients=[...@...])
    ↓
NotifyIntegration.send()
    ↓
    ├─→ AddressParser: Parse recipients
    │        ↓
    │   InternetRouter.route()
    │        ↓
    ├─→ Local Recipients → message.store_message() (was notify.send())
    │
    └─→ Remote Recipients
             ↓
         MachineRegistry.get()
             ↓
         WebSocketTransport.send_to_remote()
             ↓
         Remote notify endpoint
```

### 2.3 Address Classification

Three address types are automatically detected:

| Type | Format | Example | Detection |
|------|--------|---------|-----------|
| LOCAL | `user@local` | `alice@local` | machine matches local_machine param |
| REMOTE | `user@machine` | `bob@machine1` | single-label machine name |
| FEDERATED | `user@fqdn` | `charlie@remote.example.com` | contains dot (domain) |

## 3. Public API

### 3.1 High-Level Convenience Function

```python
from bbsengine6.net import send_with_internet

result = send_with_internet(
    channel: str,                       # Channel/topic name (was: notification_type)
    recipients: List[str],              # ["alice@local", "bob@machine1"]
    template: str,
    template_vars: Optional[Dict] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict] = None,
    urgency: Optional[Urgency] = None,
    should_persist: bool = True,
    conn: Optional[Connection] = None,
    local_machine: str = "local",
) -> Dict[str, Any]
```

**Returns**:
```python
{
    "local": Notification | None,           # Result from message.store_message() (was notify.send())
    "remote": Dict[str, Tuple[bool, str]],  # {machine: (success, message)}
    "errors": Dict[str, str],               # {address: error_message}
    "summary": Tuple[int, int],             # (success_count, failure_count)
}
```

### 3.2 Address Parsing API

```python
from bbsengine6.net import (
    AddressParser, 
    parse_address,
    is_internet_address,
)

# Parse a single address
addr = parse_address("alice@machine1")
# → InternetAddress(user="alice", machine="machine1", address_type=REMOTE)

# Check if address looks like internet address
if is_internet_address("alice@local"):
    # Do something

# Create parser with custom local machine
parser = AddressParser(local_machine="myhost")
addr = parser.parse("alice@myhost")
# → type is LOCAL (because machine == local_machine)
```

### 3.3 Routing API

```python
from bbsengine6.net import route_recipients, InternetRouter

# Simple routing
local, remote, errors = route_recipients(
    ["alice@local", "bob@machine1", "charlie@domain.com"]
)
# local = ["alice"]
# remote = {"machine1": ["bob"], "domain.com": ["charlie"]}
# errors = {}

# Advanced routing with custom registry
from bbsengine6.net import InternetRouter, get_registry

router = InternetRouter(local_machine="myhost", registry=get_registry())
local, remote, errors = router.route([...])

# Resolve machine config
host, port, token = router.resolve_machine("machine1")
```

### 3.4 Machine Registry API

```python
from bbsengine6.net import get_registry, MachineConfig

registry = get_registry()

# Register a machine
registry.register(
    machine_name="machine1",
    host="remote.example.com",
    port=8765,
    auth_token="secret123",
    tls_enabled=True,
    verify_cert=True,
)

# Get machine config
config = registry.get("machine1")
# → MachineConfig(machine_name="machine1", host="...", port=..., ...)

# Get WebSocket URL
ws_url = config.ws_url()
# → "wss://remote.example.com:8765/notify"

# List all machines
machines = registry.list_all()

# Unregister
registry.unregister("machine1")
```

### 3.5 Integration API

```python
from bbsengine6.net import NotifyIntegration, get_integration

# Create integration instance
integration = NotifyIntegration(
    local_machine="local",
    notify_module=None,  # Auto-imported if None
    registry=None,        # Default registry if None
)

# Send notifications
result = integration.send(
    channel="test",
    recipients=["alice@local", "bob@machine1"],
    template="Hello {name}",
    template_vars={"name": "World"},
)

# Check capability
if integration.can_send_to(recipients):
    # Safe to proceed
    pass

# Get default integration instance
integration = get_integration()
```

## 4. Database Schema

### 4.1 Machine Registry Table

```sql
CREATE TABLE postoffice.machine_registry (
    machine_name TEXT PRIMARY KEY,
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 8765,
    auth_token TEXT,
    tls_enabled BOOLEAN DEFAULT FALSE,
    verify_cert BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Fields**:
- `machine_name`: Unique identifier (e.g., "machine1", "remote.example.com")
- `host`: Hostname or IP address
- `port`: WebSocket port (default: 8765)
- `auth_token`: Optional authentication token for remote connection
- `tls_enabled`: Use WSS (WebSocket Secure) instead of WS
- `verify_cert`: Verify TLS certificate (if tls_enabled=true)

## 5. WebSocket Protocol

### 5.1 Notification Payload

**Send (Client → Server)**:
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

**Response (Server → Client)**:
```json
{
    "success": true,
    "message": "Notification processed",
    "delivered": 2
}
```

### 5.2 Error Handling

```json
{
    "success": false,
    "error": "Invalid recipients list",
    "code": "INVALID_PAYLOAD"
}
```

## 6. Error Handling & Edge Cases

### 6.1 Invalid Addresses

Invalid addresses are collected in the `errors` dict:

```python
result = send_with_internet(
    channel="test",
    recipients=["alice@local", "invalid", "@nomachine"],
    template="Test",
)

# result["errors"] = {
#     "invalid": "Invalid address format (expected user@machine)",
#     "@nomachine": "Invalid address format (expected user@machine)",
# }
```

### 6.2 Missing Machine Config

If a remote machine is not registered:

```python
result["remote"]["machine1"] = (
    False,
    "Machine not configured in registry: machine1"
)
```

### 6.3 Missing `message` module

If `bbsengine6.message` is not available (historical:
"missing `notify` module"):

```python
result["local"] = None
result["errors"]["all"] = "bbsengine6.message not available"
result["summary"] = (0, num_recipients)
```

### 6.4 WebSocket Timeout

If connection times out:

```python
result["remote"]["machine1"] = (
    False,
    "WebSocket timeout after 10.0s"
)
```

## 7. Implementation Details

### 7.1 Address Validation

Regex pattern: `^([a-zA-Z0-9._%-]+)@([a-zA-Z0-9.-]+)$`

- **User part**: alphanumeric, dot, underscore, percent, hyphen
- **Machine part**: alphanumeric, dot, hyphen

Examples of valid addresses:
- `alice@local`
- `bob.smith@machine1`
- `charlie_user@remote.example.com`
- `dave-user@host-name.org`

### 7.2 Thread Safety

- AddressParser: Thread-safe (no state mutation)
- InternetRouter: Thread-safe (no state mutation)
- MachineRegistry: Thread-safe with locks for cache updates
- WebSocketTransport: Thread-safe (async/sync wrapper)

### 7.3 Performance Considerations

1. **Caching**: MachineRegistry caches configs to avoid repeated DB queries
2. **Batch Processing**: Recipients grouped by machine before sending
3. **Async Transport**: WebSocketTransport uses asyncio for non-blocking I/O
4. **Lazy Imports**: notify module imported only when needed

## 8. Testing

### 8.1 Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `address.py` | 11 | 100% |
| `router.py` | 8 | 100% |
| `transport.py` | 4 | 100% |
| `integration.py` | 14 | 100% |
| `registry.py` | 10 | 100% |
| **Total** | **47** | **100%** |

### 8.2 Test Files

```
tests/
├── test_internet.py              # Phase 1: address, router, transport
├── test_internet_integration.py   # Phase 2: integration with notify
└── test_internet_registry.py      # Phase 3: registry, WebSocket protocol
```

### 8.3 Running Tests

```bash
# All internet tests
pytest py/src/bbsengine6/tests/test_internet*.py -v

# Specific test class
pytest py/src/bbsengine6/tests/test_internet.py::TestAddressParser -v

# With coverage
pytest py/src/bbsengine6/tests/test_internet*.py --cov=bbsengine6.net
```

## 9. Configuration

### 9.1 Environment Variables

None required. Optional:

- `BBSENGINE6_DBNAME`: Database name for machine registry (default: "bbsengine6")

### 9.2 Application Initialization

```python
from bbsengine6.net import get_registry

# Register your machines once at startup
registry = get_registry()
registry.register("machine1", "remote.example.com", 8765, "token123")
registry.register("machine2", "other.example.com", 8765)
```

## 10. Migration Guide

### 10.1 From `message.store_message()` to `send_with_internet()`

> **Note (2026-07-22):** The "Before" example originally showed
> `from bbsengine6 import notify; notify.send(...)`. The notify
> package was deleted in Phase 7 of
> `TODO-message-migration.md`; the live equivalent is
> `from bbsengine6 import message; message.store_message(...)`.
> The structure of the migration (one local call → unified
> local+remote call) is unchanged.
>
> **Note (Phase 11, 2026-09-01):** `bbsengine6.message.store_message`
> is unchanged at the package surface. Internally it delegates to
> `bbsengine6.message.service.store_message`, which delegates to
> `bbsengine6.message.dal.messages.store_message_with_recipients`.
> The integration layer at `bbsengine6/net/integration.py` does not
> need any change.

**Before** (local only):
```python
from bbsengine6 import message

message.store_message(
    channel="message",
    recipients=["alice", "bob"],
    template="New message",
)
```

**After** (local + remote):
```python
from bbsengine6.net import send_with_internet

send_with_internet(
    channel="message",
    recipients=["alice@local", "bob@machine1"],
    template="New message",
)
```

### 10.2 Machine Registration

**One-time setup**:
```python
from bbsengine6.net import get_registry

registry = get_registry()
registry.register("machine1", "host1.example.com", 8765, auth_token="secret")
```

## 11. Future Roadmap

### Phase 4: Production WebSocket Implementation
- Use `websockets` library
- Connection pooling
- Automatic reconnection
- Message queuing on timeout

### Phase 5: Advanced Routing
- DNS SRV record support
- Load balancing across replicas
- Retry policies and backoff
- Circuit breaker pattern

### Phase 6: Federation
- Server mesh support
- Cross-domain routing
- Trust relationships
- Federation protocol

### Phase 7: Monitoring & Analytics
- Message delivery tracking
- Performance metrics
- Error reporting dashboard
- Message audit logs

## 12. Known Limitations

1. **WebSocket Implementation**: Currently placeholder. Phase 4 will add production implementation using `websockets` library.

2. **Database**: Requires PostgreSQL for machine_registry table. Will be auto-created on first use.

3. **Authentication**: Simple token-based. Phase 6 will add more sophisticated auth.

4. **Routing**: Direct point-to-point. Phase 5 will add mesh routing.

5. **Persistence**: Remote delivery not persisted on client. Phase 4 will add delivery queues.

## 13. Examples

### Example 1: Basic Inter-Machine Messaging

```python
from bbsengine6.net import send_with_internet, get_registry

# Register machines (once at startup)
registry = get_registry()
registry.register("support-desk", "desk.company.com", 8765)
registry.register("mobile", "mobile.company.com", 8765)

# Send message to multiple machines
result = send_with_internet(
    channel="alert",
    recipients=[
        "alice@local",           # Local user
        "bob@support-desk",      # Remote user on support-desk
        "carol@mobile",          # Remote user on mobile
    ],
    template="Alert: System status check",
    sender_moniker="system",
)

# Check results
if result["summary"][1] > 0:
    print(f"Failed: {result['errors']}")
```

### Example 2: Address Parsing

```python
from bbsengine6.net import parse_address, AddressType

recipients = ["alice@local", "bob@machine1", "charlie@remote.example.com"]

for addr_str in recipients:
    addr = parse_address(addr_str)
    if addr.is_local():
        print(f"{addr.user} is local")
    elif addr.is_remote():
        print(f"{addr.user} is on {addr.machine}")
    else:
        print(f"{addr.user} is federated on {addr.machine}")
```

### Example 3: Custom Routing

```python
from bbsengine6.net import InternetRouter, get_registry

router = InternetRouter("myhost")
recipients = ["alice@myhost", "bob@other", "charlie@external.com"]

local, remote, errors = router.route(recipients)

print(f"Local: {local}")              # ["alice"]
print(f"Remote: {remote}")             # {"other": ["bob"], "external.com": ["charlie"]}
print(f"Errors: {errors}")             # {}

# Resolve machine configs
for machine, users in remote.items():
    host, port, token = router.resolve_machine(machine)
    if host:
        print(f"Send to {machine} at {host}:{port}")
    else:
        print(f"No config for {machine}")
```

## 14. Appendix: Type Definitions

```python
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

class AddressType(Enum):
    LOCAL = "local"
    REMOTE = "remote"
    FEDERATED = "federated"

@dataclass
class InternetAddress:
    user: str
    machine: str
    full_address: str
    address_type: AddressType

@dataclass
class ParseResult:
    valid: List[InternetAddress]
    invalid: Dict[str, str]

@dataclass
class MachineConfig:
    machine_name: str
    host: str
    port: int
    auth_token: Optional[str] = None
    tls_enabled: bool = False
    verify_cert: bool = True

    def ws_url(self) -> str:
        protocol = "wss" if self.tls_enabled else "ws"
        return f"{protocol}://{self.host}:{self.port}/notify"
```

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-20  
**Maintainer**: OpenCode  
**Status**: Stable
