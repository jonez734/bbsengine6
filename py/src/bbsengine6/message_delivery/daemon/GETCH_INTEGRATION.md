# NotifyD with getch() - No Daemon Required

**See Also**: [BBSENGINE6_NOTIFYD_ARCHITECTURE.md](../../BBSENGINE6_NOTIFYD_ARCHITECTURE.md#model-2-getch-integration-recommended-for-bbs) for full architecture details

## Overview

NotifyD can work **without a background daemon** by leveraging bbsengine6's existing `getch()` notification system. This is ideal for a BBS where users are actively at the terminal - notifications are checked during normal keyboard input.

## How It Works

### Traditional Daemon Model (Legacy)
```
Background daemon thread continuously polls IMAP servers
    ↓
Notifications accumulate in bbsengine6.notify queue
    ↓
Users see notifications when they call getch()
```

### getch() Integration Model (Recommended for BBS)
```
User calls getch() during normal menu navigation
    ↓
getch() checks for pending notifications
    ↓
If notifications found, bell emits and F2 shows them
    ↓
No separate daemon needed
```

### IMAP Polling Options

**Option 1: Passive (No IMAP daemon)**
- Only user-fired events via `notifyd.fire_event()` are sent
- No automatic email monitoring
- Simplest deployment

**Option 2: Scheduled IMAP Polling**
- Cron job or scheduler periodically polls IMAP servers
- Results added to notification queue
- No persistent background process

**Option 3: Event-Triggered IMAP**
- IMAP polling triggered by user login or specific events
- Email notifications only when requested
- Hybrid approach

## Setup: getch() Integration Model

### 1. Configuration (Same as Daemon)

Create `/etc/bbsengine6/notifyd.json`:

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["admin@example.com"],
      "template": "user-login.tmpl",
      "urgency": "high"
    },
    "message-received": {
      "recipients": ["user"],
      "template": "message.tmpl",
      "urgency": "high"
    }
  },
  "notification_settings": {
    "enabled": true,
    "log_history": true
  }
}
```

### 2. Fire Events from BBSEngine6 Code

No daemon needed - just fire events when they occur:

```python
# In bbsengine6 login handler
import bbsengine6.notifyd as notifyd

def on_user_login(user, request):
    # ... login logic ...
    
    # Fire notification event
    notifyd.fire_event("user-login", {
        "username": user.username,
        "timestamp": datetime.now().isoformat(),
    })
```

### 3. Enable getch() Notification Checking

The `getch()` function already checks for notifications by default. Users will:

- ✅ See a bell (🔔) when notifications arrive
- ✅ Press F2 to view pending notifications
- ✅ Notifications display in-terminal with colors and formatting

**No additional code needed** - it's built into getch()!

### 4. Optional: Scheduled IMAP Polling

If you want automatic email monitoring without a daemon, use a cron job:

```bash
# /etc/cron.d/notifyd-imap-poll
*/5 * * * * bbsengine6 /usr/bin/python3 -m bbsengine6.notifyd poll-imap

# Or with systemd timer
# /etc/systemd/system/notifyd-imap.timer
[Unit]
Description=NotifyD IMAP Polling Timer
Requires=notifyd-imap.service

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

Create the poll-imap command in cli.py:

```python
def cmd_poll_imap(args: argparse.Namespace) -> int:
    """
    Poll IMAP servers once and send notifications.
    
    Intended for cron or systemd timer, not continuous daemon.
    """
    try:
        cfg = config_module.load_config(args.config)
        
        # Poll each IMAP server once
        for server_config in cfg.get("imap_servers", []):
            try:
                # Connect and get new emails
                imap_data = imap_monitor.poll_imap_all_mailboxes(
                    [server_config],
                    cfg.get("credentials", {})
                )
                
                # Send notifications for each email
                for email in imap_data:
                    notification_module.send_imap_notification(
                        email,
                        server_config.get("name"),
                        cfg
                    )
                    
            except Exception as e:
                logging.error(f"IMAP poll failed for {server_config.get('name')}: {e}")
                continue
        
        return 0
        
    except Exception as e:
        logging.error(f"IMAP poll failed: {e}", exc_info=args.debug)
        return 1
```

## Comparison: Daemon vs getch() Model

| Feature | Daemon Model | getch() Model |
|---------|--------------|---------------|
| **Continuous polling** | ✅ Yes (background thread) | ❌ No (requires cron) |
| **Always-on monitoring** | ✅ Yes | ❌ No (checks on demand) |
| **Complexity** | Higher (thread management) | Lower (integrated) |
| **BBS-friendly** | Good | Better (fits terminal paradigm) |
| **Event firing** | ✅ Works | ✅ Works |
| **IMAP monitoring** | ✅ Built-in | ⚠️ Requires scheduling |
| **Resource usage** | Higher (persistent process) | Minimal (no daemon) |
| **Deployment** | Systemd service | Simple script calls |

## Implementation: Event-Only (No IMAP Polling)

**Best for**: BBS systems that only fire application events

### Step 1: Keep notifyd Module Minimal

The core notifyd functionality is just event firing - no daemon needed:

```python
# bbsengine6/notifyd/__init__.py
from .event_system import fire_event, register_event_listener

__all__ = ["fire_event", "register_event_listener"]
```

### Step 2: Load Config on Demand

```python
# bbsengine6/notifyd/__init__.py
from . import config as config_module
from . import notification as notification_module

_config = None

def get_config():
    global _config
    if _config is None:
        try:
            _config = config_module.load_config()
        except Exception:
            _config = {}
    return _config

def fire_event(event_name: str, variables: dict) -> None:
    """Fire an event (uses bbsengine6.notify infrastructure)."""
    cfg = get_config()
    listeners = cfg.get("event_listeners", {})
    
    if event_name not in listeners:
        return  # No listener configured
    
    listener_config = listeners[event_name]
    dispatcher = notification_module.NotificationDispatcher(storage=None)
    
    dispatcher.send_custom_notification(
        event_type=event_name,
        recipients=listener_config.get("recipients", []),
        template=listener_config.get("template"),
        urgency=listener_config.get("urgency", "ROUTINE"),
        template_vars=variables
    )
```

### Step 3: Fire Events in bbsengine6 Code

```python
# Any bbsengine6 module
import bbsengine6.notifyd as notifyd

# Fire an event when something happens
notifyd.fire_event("user-login", {
    "username": "john.doe",
    "ip_address": "192.168.1.100",
})
```

### Step 4: Users See Notifications in getch()

```python
# In terminal loop
from bbsengine6.io import getch

while True:
    key = getch.getch_str(timeout=1.0)  # Checks notifications automatically
    
    # key might be None if F2 was pressed to view notifications
    if key is None:
        continue
    
    # Process key...
```

## Implementation: Scheduled IMAP Polling

**Best for**: BBS systems that want email monitoring without daemon

### Step 1: Add poll-imap Command

```python
# In bbsengine6/notifyd/cli.py

def cmd_poll_imap(args: argparse.Namespace) -> int:
    """
    Poll IMAP servers once for new emails.
    
    Intended to be run from cron/systemd-timer, not as daemon.
    """
    try:
        cfg = config_module.load_config(args.config)
        pool = database.get_pool()
        
        # Create storage for state tracking
        storage = storage_module.Storage(pool)
        storage.ensure_schema()
        
        imap_servers = cfg.get("imap_servers", [])
        credentials_config = cfg.get("credentials", {})
        
        # Poll each server once
        total_notifications = 0
        for server_config in imap_servers:
            try:
                logging.info(f"Polling {server_config.get('name')}")
                
                # Get new emails for this server
                emails = imap_monitor.poll_imap_all_mailboxes(
                    [server_config],
                    credentials_config,
                    storage
                )
                
                # Send notification for each email
                for email in emails:
                    dispatcher.send_imap_notification(
                        email,
                        server_config.get("name"),
                        cfg
                    )
                    total_notifications += 1
                    
            except Exception as e:
                logging.error(f"Failed to poll {server_config.get('name')}: {e}")
                continue
        
        logging.info(f"Poll complete: {total_notifications} notifications sent")
        return 0
        
    except Exception as e:
        logging.error(f"Poll failed: {e}", exc_info=args.debug)
        return 1
```

### Step 2: Set Up Cron Job

```bash
# /etc/cron.d/notifyd-poll
# Poll IMAP every 5 minutes
*/5 * * * * bbsengine6 /usr/bin/python3 -m bbsengine6.notifyd poll-imap

# Or just during business hours
*/5 9-17 * * 1-5 bbsengine6 /usr/bin/python3 -m bbsengine6.notifyd poll-imap
```

### Step 3: Monitor with Logs

```bash
# View recent polls
tail -f /var/log/bbsengine6/notifyd.log | grep "Polling\|Poll complete"

# Check for errors
journalctl -u cron -f | grep notifyd
```

## Minimal Setup: Event-Only

**Simplest possible setup** - Just event firing, no IMAP, no daemon:

### 1. Create minimal config

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["admin"],
      "template": "user-login.tmpl",
      "urgency": "high"
    }
  },
  "notification_settings": {
    "enabled": true,
    "log_history": false
  }
}
```

### 2. Fire event when user logs in

```python
import bbsengine6.notifyd as notifyd

def on_login(user):
    notifyd.fire_event("user-login", {"username": user.name})
```

### 3. User sees notification during getch()

```python
from bbsengine6.io import getch

# Already checks for notifications!
key = getch.getch_str()  # Bell emits if notification pending
```

**Total setup time**: 5 minutes. **Running processes**: 0.

## Comparing to Daemon Model

### Daemon Model Issues for BBS

1. **Always consuming resources** - Background thread even when idle
2. **Separate lifecycle** - Daemon and BBS are independent processes
3. **Deployment complexity** - Systemd service, environment vars, etc.
4. **Harder to debug** - Background thread behavior unclear
5. **State management** - Persistent connections to IMAP servers
6. **Overkill for events** - Not needed for just firing events

### getch() Model Advantages for BBS

1. **Event-driven** - Check on demand during user interaction
2. **Minimal resources** - No persistent background threads
3. **Simple deployment** - Just configuration file
4. **Fits terminal paradigm** - Notifications checked during I/O
5. **Integrated** - Uses bbsengine6's existing notify system
6. **Debugging** - Everything happens during getch() calls
7. **Scalability** - Works with multiple concurrent users

## Migration Path: Daemon → getch()

If you're currently using the daemon model, migration is simple:

### Step 1: Disable Daemon

```bash
sudo systemctl stop notifyd
sudo systemctl disable notifyd
```

### Step 2: Keep Config and Event Firing

No changes needed - events still fire the same way.

### Step 3: Verify Notifications Work

```python
# Test event firing
import bbsengine6.notifyd as notifyd

notifyd.fire_event("test-event", {
    "message": "This should appear in getch()"
})

# Now call getch() - you should see bell and F2 option
from bbsengine6.io import getch
key = getch.getch_str(timeout=5.0)
```

### Step 4: Remove Daemon Code

Keep notifyd module but only use event firing functionality:

```python
# bbsengine6/notifyd/__init__.py
from .event_system import fire_event

# Remove daemon imports:
# from .daemon import start_daemon, stop_daemon  ❌

__all__ = ["fire_event"]
```

## Recommendation for bbsengine6

**Use getch() Integration Model because:**

1. ✅ **Fits BBS paradigm** - Notifications during user interaction
2. ✅ **Minimal overhead** - No persistent background process
3. ✅ **Already implemented** - getch() already has notification support
4. ✅ **Event-driven** - Perfect for application events
5. ✅ **Simple deployment** - Just configuration file
6. ✅ **Scales better** - No thread per concurrent user
7. ✅ **Debugging** - Everything synchronous during getch()

**When to use Daemon Model:**
- Need continuous IMAP monitoring without user interaction
- Desktop email client use case
- Monitoring 24/7 for critical alerts

**When to use getch() Model:** (Recommended)
- BBS with users at terminal
- Event-based notifications (user login, messages, etc.)
- Want to minimize resource usage
- Prefer integrated solution

## Summary

| Component | Daemon Model | getch() Model |
|-----------|--------------|---------------|
| **Background polling** | ✅ daemon.py | ❌ Removed |
| **Event firing** | ✅ hooks.py, notification.py | ✅ Same code |
| **IMAP monitoring** | ✅ imap_monitor.py + daemon | ⚠️ Cron/timer only |
| **Notification display** | getch() checks queue | ✅ getch() checks queue |
| **Running processes** | 1 daemon + BBS | Just BBS |
| **Setup complexity** | Medium | Low |
| **BBS-friendliness** | Good | Better |

**Conclusion**: For bbsengine6 BBS, the **getch() integration model is superior** because it eliminates the daemon while keeping all the functionality users need.
