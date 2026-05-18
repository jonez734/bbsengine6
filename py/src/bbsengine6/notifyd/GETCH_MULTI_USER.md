# getch() Integration: Multi-Member Per Machine Support

## Short Answer

**YES! getch() integration DOES allow for proper multi-member per machine notifications.**

This is actually **better than the daemon model** for multi-member scenarios because it's inherently member-aware.

## How It Works

### The Architecture

```
Member 1 (moniker="john")
  ↓
getch() calls during keyboard input
  ↓
Gets notifications from john's queue
  ↓
Displays ONLY john's notifications
  
Member 2 (moniker="jane")
  ↓
getch() calls during keyboard input
  ↓
Gets notifications from jane's queue
  ↓
Displays ONLY jane's notifications
```

### Key Components

**1. Member Identity (moniker)**
```python
# From bbsengine6/member.py _threadlocal
from bbsengine6.member import _threadlocal

moniker = getattr(_threadlocal, "moniker", None)  # Moniker of current member

# Each member gets their own isolated notifications
```

**2. Per-Member Notification Queue**
```python
# From bbsengine6/notify.py
_queues = {}  # Dict[moniker, UserNotificationQueue]

def get_queue(moniker: str) -> UserNotificationQueue:
    """Get the in-memory notification queue for this specific member."""
    with _queues_lock:
        if moniker not in _queues:
            _queues[moniker] = UserNotificationQueue()
        return _queues[moniker]
```

**3. Member-Specific getch() Checks**
```python
# From bbsengine6/io/getch.py line 533-540
moniker = getattr(_threadlocal, "moniker", None)  # Get CURRENT member

if check_notifications and moniker and _has_notify_module:
    # Count notifications for THIS member only
    has_notifications = notify.count(moniker)
    if has_notifications:
        _emit_notification_bell_once()
```

**4. Member-Specific Display**
```python
# From bbsengine6/io/getch.py line 547-548
if result == "KEY_F2" and moniker:
    # Show notifications for THIS member only
    _show_pending_notifications(moniker)
```

## Multi-Member Scenario Example

### Setup: Three Members on Same Machine

**Member 1 (john)**
```bash
# Logs in from terminal 1
ssh bbs@host
(enters moniker: john)
```

**Member 2 (jane)**
```bash
# Logs in from terminal 2
ssh bbs@host
(enters moniker: jane)
```

**Member 3 (admin)**
```bash
# Logs in from terminal 3
ssh bbs@host
(enters moniker: admin)
```

### Notifications Fire From Events

```python
# In bbsengine6 code
import bbsengine6.notifyd as notifyd
from bbsengine6.member import _threadlocal
from datetime import datetime

def on_member_login(member):
    # Fire event with member context
    moniker = getattr(_threadlocal, "moniker", None)
    notifyd.fire_event("member-login", {
        "moniker": moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
```

### Each Member Sees Only Their Notifications

**Terminal 1 (john)**
```
john's menu...
[BELL] 🔔  ← john sees bell
Press F2 for notifications

(john presses F2)
─────────────────────────────
[HIGH] 2024-05-18 14:30:00
To: john
John's account accessed from 192.168.1.100
─────────────────────────────
(continues with john's notifications only)
```

**Terminal 2 (jane)**
```
jane's menu...
(no bell - jane has no notifications)

(later, jane fires event with her moniker)
[BELL] 🔔  ← jane sees bell only for her notifications
Press F2 for notifications
```

**Terminal 3 (admin)**
```
admin's menu...
(admin sees only admin notifications)
```

### Key Points

✅ Each member's `getch()` call checks **ONLY their own queue**
✅ Notifications are **isolated per member**
✅ Member identity comes from `_threadlocal.moniker` (thread-local storage)
✅ No cross-member notification leakage
✅ Built-in to bbsengine6 architecture

## How to Use: Multi-Member with getch()

### 1. Fire Events with Member Context

Always include the member context when firing events:

```python
# bbsengine6/login.py
import bbsengine6.notifyd as notifyd
from datetime import datetime
from bbsengine6.member import _threadlocal

def on_member_login(member, request):
    # Login logic...
    
    # Fire event - member context already in _threadlocal.moniker
    moniker = getattr(_threadlocal, "moniker", None)
    notifyd.fire_event("member-login", {
        "moniker": moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
```

### 2. Route to Member's Queue

In your notification dispatcher:

```python
# bbsengine6/notifyd/__init__.py
import bbsengine6.notify as notify
from bbsengine6.member import _threadlocal

def fire_event(event_name: str, variables: dict) -> None:
    """Fire an event - automatically routes to current member's queue."""
    
    cfg = get_config()
    listeners = cfg.get("event_listeners", {})
    
    if event_name not in listeners:
        return
    
    listener_config = listeners[event_name]
    current_moniker = getattr(_threadlocal, "moniker", None)
    
    if not current_moniker:
        return  # No member context
    
    # Send to THIS member's queue
    notify.notify(
        moniker=current_moniker,
        recipients=listener_config.get("recipients", []),
        message=render_template(
            listener_config.get("template"),
            variables
        ),
        urgency=listener_config.get("urgency", "ROUTINE"),
    )
```

### 3. getch() Displays Member-Specific Notifications

No changes needed - getch() already does this:

```python
# In main loop
from bbsengine6.io import getch

while True:
    key = getch.getch_str(timeout=1.0)
    # Automatically checks/displays current member's notifications
    # Bell emits only for THAT member
    # F2 shows only THAT member's notifications
```

## Configuration: Multi-Member Setup

### Minimal Config (Same for All Members)

```json
{
  "event_listeners": {
    "member-login": {
      "recipients": ["john", "jane", "admin"],
      "template": "member-login.tmpl",
      "urgency": "high"
    },
    "message-received": {
      "recipients": ["member"],
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

**Note**: "member" in recipients means "the member who triggered the event" (their moniker)

### Advanced: Different Events for Different Members

```json
{
  "event_listeners": {
    "sysop-action": {
      "recipients": ["sysop", "audit-log"],
      "template": "sysop-action.tmpl",
      "urgency": "high"
    },
    "member-message": {
      "recipients": ["member"],  # Notifies the recipient member
      "template": "message.tmpl",
      "urgency": "medium"
    }
  }
}
```

## Implementation Example: Multi-Member BBS

### 1. Member Login

```python
# bbsengine6/login.py
import bbsengine6.notifyd as notifyd
from bbsengine6.member import _threadlocal
from datetime import datetime

def handle_member_login(moniker, password, request):
    member = verify_login(moniker, password)
    
    if not member:
        # Fire failed login event
        notifyd.fire_event("login-failed", {
            "moniker": moniker,
            "ip_address": request.remote_addr,
        })
        raise AuthenticationError()
    
    # Fire successful login - goes to member's queue
    current_moniker = getattr(_threadlocal, "moniker", None)
    notifyd.fire_event("member-login", {
        "moniker": current_moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
    
    return member
```

### 2. Message Notification

```python
# bbsengine6/messages.py
import bbsengine6.notifyd as notifyd
from bbsengine6.member import _threadlocal

def send_message(to_moniker, text):
    # Save message...
    from_moniker = getattr(_threadlocal, "moniker", None)
    msg = Message.create(
        from_moniker=from_moniker,
        to_moniker=to_moniker,
        text=text
    )
    
    # Notify recipient - goes to THEIR queue
    notifyd.fire_event("message-received", {
        "from_moniker": from_moniker,
        "message_preview": text[:50],
        "timestamp": datetime.now().isoformat(),
    })
```

### 3. Sysop Actions

```python
# bbsengine6/sysop.py
import bbsengine6.notifyd as notifyd
from bbsengine6.member import _threadlocal

def delete_post(post_id):
    post = Post.get(post_id)
    
    # Delete...
    post.delete()
    
    # Notify sysop and audit log
    sysop_moniker = getattr(_threadlocal, "moniker", None)
    notifyd.fire_event("sysop-action", {
        "action": "delete_post",
        "sysop": sysop_moniker,
        "post_id": post_id,
        "timestamp": datetime.now().isoformat(),
    })
```

### 4. Terminal Loop (No Changes Needed)

```python
# bbsengine6/main.py
from bbsengine6.io import getch

def main_loop():
    while True:
        display_menu()
        
        # getch() automatically:
        # 1. Gets current member's moniker from _threadlocal
        # 2. Checks THAT member's notification queue
        # 3. Emits bell only if THAT member has notifications
        # 4. Shows F2 option for THAT member's notifications
        key = getch.getch_str(timeout=1.0)
        
        if key == "Q":
            break
        
        process_key(key)
```

## Comparison: Daemon vs getch() for Multi-Member

| Feature | Daemon Model | getch() Model |
|---------|--------------|---------------|
| **Multi-member support** | ❌ Limited (shared config) | ✅ Full (per-member queues) |
| **Member isolation** | ❌ No | ✅ Yes |
| **Notifications per member** | ❌ Global queue | ✅ Per-member queue |
| **Privacy** | ❌ Members can see others' notifications | ✅ Only their own |
| **Thread-local integration** | ❌ No | ✅ Yes |
| **Concurrent members** | ⚠️ Works but messy | ✅ Clean design |
| **Implementation** | Complex | Simple |
| **Code changes needed** | Medium | Minimal |

## Recommended Architecture: Multi-Member BBS

### Use getch() Integration Because:

1. **✅ Built-in member isolation** - Each member gets their own queue
2. **✅ Thread-local integration** - Moniker from `_threadlocal.moniker`
3. **✅ Simple deployment** - No daemon needed
4. **✅ Scales to multiple members** - Each member's getch() checks their queue
5. **✅ Event-driven** - Fire events with member context
6. **✅ Privacy-respecting** - Members only see their notifications
7. **✅ BBS-friendly** - Notifications during keyboard I/O

### Architecture Diagram

```
Member 1 Session        Member 2 Session        Member 3 Session
    │                       │                       │
    └──→ getch() ─→ Check moniker "john"           │
         bell if john's queue has notifications    │
         │                                          │
         └──→ Member 2 getch() ─→ Check moniker "jane"
              bell if jane's queue has notifications
              │
              └──→ Member 3 getch() ─→ Check moniker "admin"
                   bell if admin's queue has notifications

Shared config.json (same for all members)
Separate notification queues per member
```

## Migration: Daemon → getch() for Multi-Member

If you're currently trying to use daemon for multi-member:

### Step 1: Remove Daemon

```bash
sudo systemctl stop notifyd
sudo systemctl disable notifyd
```

### Step 2: Update Code to Use getch() Integration

```python
# Instead of manually polling or starting daemon:
# Just fire events with member context

from bbsengine6.member import _threadlocal

notifyd.fire_event("event-name", {
    "moniker": getattr(_threadlocal, "moniker", None),  # Include moniker
    "data": "..."
})
```

### Step 3: Ensure getch() is Called

```python
# Terminal loop automatically checks notifications
key = getch.getch_str(timeout=1.0)
# That's it! getch() handles everything
```

## Summary

**getch() integration is superior for multi-member per machine because:**

1. Member identity is automatically from `_threadlocal.moniker`
2. bbsengine6.notify already has per-member queues
3. getch() already filters by current member
4. Built-in privacy/isolation
5. No daemon overhead
6. Scales elegantly to multiple concurrent members

**This is the recommended approach for bbsengine6 BBS multi-member support.**

See [GETCH_INTEGRATION.md](GETCH_INTEGRATION.md) for implementation details.
