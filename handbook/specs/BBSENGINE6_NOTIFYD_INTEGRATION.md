# bbsengine6 notifyd - Integration Points

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## bbsengine6 Module Imports

### In notification.py

```python
from bbsengine6 import notify
from bbsengine6.notify import NotificationUrgency
```

Calls `notify.send()` to route notifications through bbsengine6's infrastructure.

### In daemon.py

```python
from bbsengine6 import database
from bbsengine6.database import getpool
```

Gets connection pool for PostgreSQL state tracking.

### In event_listener.py (Optional)

```python
try:
    from bbsengine6.io import register_key_event_handler
except ImportError:
    pass
```

Optional integration with bbsengine6.io.KeyEventSystem for keyboard events.

---

## bbsengine6.notify Integration

### Notification Sending

```python
import bbsengine6.notify as notify

notify.send(
    recipients=["player1", "player2"],
    message="Email from Gmail",
    template="imap-message.tmpl",
    urgency="ROUTINE"
)
```

Returns notification ID and records to `engine.__notify` table.

### Notification Queue

- Each recipient has their own notification queue
- Notifications accumulate in bbsengine6.notify
- getch() checks queue automatically
- F2 displays pending notifications

---

## Systemd Integration

### Service File

**Location**: `/etc/systemd/system/notifyd.service`

```ini
[Unit]
Description=BBSengine6 Notification Daemon
Documentation=https://bbsengine6.local/docs/notifyd
After=network.target postgresql.service
Wants=postgresql.service
PartOf=bbsengine6.target

[Service]
Type=simple
User=bbsengine6
Group=bbsengine6
WorkingDirectory=/var/lib/notifyd

ExecStart=/home/opencode/.venv/bin/python -m bbsengine6.notifyd.cli
ExecReload=/bin/kill -HUP $MAINPID
ExecStop=/bin/kill -TERM $MAINPID

Restart=always
RestartSec=10
StartLimitInterval=60s
StartLimitBurst=3

StandardOutput=journal
StandardError=journal
SyslogIdentifier=notifyd

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/notifyd /var/log/notifyd.log

[Install]
WantedBy=multi-user.target
```

### Management Commands

```bash
# Start daemon
sudo systemctl start notifyd

# Stop daemon
sudo systemctl stop notifyd

# Restart daemon
sudo systemctl restart notifyd

# Check status
sudo systemctl status notifyd

# Follow logs
sudo journalctl -u notifyd -f

# View recent logs
sudo journalctl -u notifyd -n 50

# Enable auto-start on boot
sudo systemctl enable notifyd

# Disable auto-start
sudo systemctl disable notifyd
```

---

## Event Hook Registration

### Module-Level API

```python
from bbsengine6 import notifyd

# Fire an event
notifyd.fire_event("user.login", {
    "moniker": "john",
    "ip_address": "192.168.1.100"
})
```

### Integration Points in bbsengine6

#### In member.py (Login/Logout)

```python
from bbsengine6.notifyd import fire_event
from datetime import datetime

def on_login(moniker: str):
    # ... existing login code ...
    fire_event("user.login", {
        "moniker": moniker,
        "timestamp": datetime.now().isoformat()
    })

def on_logout(moniker: str):
    # ... existing logout code ...
    fire_event("user.logout", {
        "moniker": moniker,
        "timestamp": datetime.now().isoformat()
    })
```

#### In game code (empyre, etc.)

```python
from bbsengine6.notifyd import fire_event

def combat_resolved(player, attacker, result):
    # ... existing combat code ...
    fire_event("game.combat", {
        "player": player.moniker,
        "attacker": attacker.moniker,
        "result": result,
        "damage": 42
    })
```

---

## Database Connection Pooling

### Using Existing Pool

```python
from bbsengine6.database import getpool
from bbsengine6.notifyd.storage import NotificationStorage

pool = getpool()  # Get existing bbsengine6 pool
storage = NotificationStorage(pool)  # Use for notifyd
```

### No Additional Database Configuration Needed

notifyd reuses bbsengine6's existing database configuration and connection pool, eliminating duplicate setup.

---

## Public API Exports

### `notifyd/__init__.py`

```python
from .hooks import EventBus, fire_event, register_event_handler
from .daemon import NotifyDaemon
from .config import NotifydConfig

__all__ = [
    "fire_event",
    "register_event_handler",
    "NotifyDaemon",
    "NotifydConfig"
]
```

### Available Exports

- `fire_event(event_name: str, variables: dict) -> None`
  - Fire custom events from application code
- `register_event_handler(event_type: str, handler: Callable) -> None`
  - Register handlers for custom events
- `NotifyDaemon`
  - Main daemon class
- `NotifydConfig`
  - Configuration dataclass

---

For deployment and systemd setup, see [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](BBSENGINE6_NOTIFYD_DEPLOYMENT.md).

For component specifications, see [BBSENGINE6_NOTIFYD_COMPONENTS.md](BBSENGINE6_NOTIFYD_COMPONENTS.md).
