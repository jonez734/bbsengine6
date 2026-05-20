# Internet Layer Quick Start Guide

**Looking for inter-machine messaging?** You've found the right place.

The `bbsengine6.net` module adds SMTP-style addressing (`user@machine`) to the notification system, allowing you to send messages between machines and users across your network.

## Quick Navigation

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [INTERNET_LAYER_SPEC.md](../INTERNET_LAYER_SPEC.md) | **Complete specification** | 15 min |
| [INTERNET_LAYER.md](../INTERNET_LAYER.md) | Architecture overview | 10 min |
| This guide | Getting started | 5 min |

## 5-Minute Quickstart

### 1. Basic Usage

```python
from bbsengine6.net import send_with_internet

# Send to local and remote users
result = send_with_internet(
    notification_type="greeting",
    recipients=[
        "alice@local",          # Local user
        "bob@remote_machine",   # Remote user
    ],
    template="Hello {name}!",
    template_vars={"name": "World"},
)

print(f"Sent to {result['summary'][0]}, Failed: {result['summary'][1]}")
```

### 2. Register a Remote Machine (one-time setup)

```python
from bbsengine6.net import get_registry

registry = get_registry()
registry.register(
    machine_name="remote_machine",
    host="remote.example.com",
    port=8765,
)
```

### 3. Check Results

```python
result = send_with_internet(
    notification_type="test",
    recipients=["alice@local", "bob@remote_machine"],
    template="Test message",
)

# {
#     "local": Notification(...),                    # Success for local
#     "remote": {"remote_machine": (True, "...")},   # Success for remote
#     "errors": {},                                   # Any parsing errors
#     "summary": (2, 0)                              # 2 succeeded, 0 failed
# }
```

## Address Format

```
user@machine
├── LOCAL (single label machine = "local")
│   └── alice@local
├── REMOTE (single label machine != "local")
│   └── bob@server1
└── FEDERATED (contains dot = domain)
    └── charlie@remote.example.com
```

## Common Patterns

### Pattern 1: Broadcast to All Machines

```python
from bbsengine6.net import send_with_internet, get_registry

# Get all registered machines
registry = get_registry()
machines = registry.list_all()

# Build recipient list
recipients = ["alice@local"]  # Local user
for machine in machines:
    recipients.append(f"user@{machine.machine_name}")

send_with_internet(
    notification_type="system_alert",
    recipients=recipients,
    template="System maintenance at {time}",
    template_vars={"time": "2026-05-20 22:00"},
)
```

### Pattern 2: Handle Errors Gracefully

```python
result = send_with_internet(
    notification_type="message",
    recipients=["alice@local", "bob@machine1", "invalid"],
    template="New message",
)

# Check what failed
if result["errors"]:
    for addr, error in result["errors"].items():
        print(f"Error sending to {addr}: {error}")

if result["remote"]:
    for machine, (success, msg) in result["remote"].items():
        if not success:
            print(f"Failed to reach {machine}: {msg}")
```

### Pattern 3: Conditional Delivery

```python
from bbsengine6.net import route_recipients

# Separate local from remote
recipients = ["alice@local", "bob@machine1"]
local, remote, errors = route_recipients(recipients)

if local:
    # Send to local via existing notify
    from bbsengine6 import notify
    notify.send(
        notification_type="urgent",
        recipients=local,
        template="Urgent: {msg}",
        template_vars={"msg": "Action required"},
    )

if remote:
    # Handle remote specially
    for machine, users in remote.items():
        print(f"Sending to {len(users)} users on {machine}")
```

## API Reference (Quick)

### High-Level

```python
from bbsengine6.net import send_with_internet

result = send_with_internet(
    notification_type="string",
    recipients=["user@machine", ...],
    template="message with {vars}",
    template_vars={"vars": "..."},
)
# Returns: {"local": ..., "remote": {...}, "errors": {...}, "summary": (...)}
```

### Address Parsing

```python
from bbsengine6.net import parse_address, is_internet_address

addr = parse_address("alice@machine1")
# → InternetAddress(user="alice", machine="machine1", address_type=REMOTE)

if is_internet_address("alice@machine1"):
    # True
```

### Routing

```python
from bbsengine6.net import route_recipients

local, remote, errors = route_recipients(["alice@local", "bob@machine1"])
# local = ["alice"]
# remote = {"machine1": ["bob"]}
# errors = {}
```

### Machine Registry

```python
from bbsengine6.net import get_registry

registry = get_registry()

# Register
registry.register("machine1", "host.example.com", 8765, auth_token="secret")

# Query
config = registry.get("machine1")
ws_url = config.ws_url()  # "ws://host.example.com:8765/notify"

# List all
machines = registry.list_all()

# Unregister
registry.unregister("machine1")
```

### Integration with notify

```python
from bbsengine6.net import NotifyIntegration

integration = NotifyIntegration()

result = integration.send(
    notification_type="test",
    recipients=["alice@local"],
    template="Test",
)

# Check if can send
if integration.can_send_to(recipients):
    # Safe to proceed
    pass
```

## Testing

```bash
# Run all internet tests
pytest py/src/bbsengine6/tests/test_internet*.py -v

# Run specific test
pytest py/src/bbsengine6/tests/test_internet.py::TestAddressParser -v

# Check coverage
pytest py/src/bbsengine6/tests/test_internet*.py --cov=bbsengine6.net
```

All 47 tests pass ✅

## Database

Automatic table creation: `postoffice.machine_registry`

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

## Troubleshooting

### "Machine not configured in registry"

**Problem**: Trying to send to a machine that isn't registered.

**Solution**:
```python
from bbsengine6.net import get_registry

registry = get_registry()
registry.register("machine1", "host.example.com", 8765)
```

### "bbsengine6.notify not available"

**Problem**: Local recipients can't be delivered (notify module missing).

**Solution**: Install bbsengine6 with all dependencies or provide notify_module explicitly.

### "Invalid address format"

**Problem**: Address doesn't match `user@machine` pattern.

**Valid examples**:
- `alice@local` ✅
- `bob.smith@machine1` ✅
- `charlie_user@remote.example.com` ✅

**Invalid examples**:
- `alice` ❌ (missing @machine)
- `@local` ❌ (missing user)
- `alice@` ❌ (missing machine)
- `alice@bad!machine` ❌ (invalid characters)

## Next Steps

1. **Read the Spec**: See [INTERNET_LAYER_SPEC.md](../INTERNET_LAYER_SPEC.md) for complete API docs
2. **Run the Tests**: `pytest py/src/bbsengine6/tests/test_internet*.py -v`
3. **Integrate**: Use `send_with_internet()` in your application
4. **Register Machines**: Set up your machine registry at startup

## Architecture Details

For deep dive into architecture, design patterns, and future roadmap, see:
- [INTERNET_LAYER.md](../INTERNET_LAYER.md) - Architecture overview
- [INTERNET_LAYER_SPEC.md](../INTERNET_LAYER_SPEC.md) - Complete specification

---

**Questions?** Check the spec or run the tests to see examples.
