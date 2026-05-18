# getch() Integration: Multi-User Per Machine Support

## Short Answer

**YES! getch() integration DOES allow for proper multi-user per machine notifications.**

This is actually **better than the daemon model** for multi-user scenarios because it's inherently user-aware.

## How It Works

### The Architecture

```
User 1 (moniker="john")
  ↓
getch() calls during keyboard input
  ↓
Gets notifications from john's queue
  ↓
Displays ONLY john's notifications
  
User 2 (moniker="jane")
  ↓
getch() calls during keyboard input
  ↓
Gets notifications from jane's queue
  ↓
Displays ONLY jane's notifications
```

### Key Components

**1. User Identity (moniker)**
```python
# From bbsengine6/member.py _threadlocal
moniker = getattr(_threadlocal, "moniker", None)  # Username of current user

# Each user gets their own isolated notifications
```

**2. Per-User Notification Queue**
```python
# From bbsengine6/notify.py
_queues = {}  # Dict[moniker, UserNotificationQueue]

def get_queue(moniker: str) -> UserNotificationQueue:
    """Get the in-memory notification queue for this specific user."""
    with _queues_lock:
        if moniker not in _queues:
            _queues[moniker] = UserNotificationQueue()
        return _queues[moniker]
```

**3. User-Specific getch() Checks**
```python
# From bbsengine6/io/getch.py line 533-540
moniker = getattr(_threadlocal, "moniker", None)  # Get CURRENT user

if check_notifications and moniker and _has_notify_module:
    # Count notifications for THIS user only
    has_notifications = notify.count(moniker)
    if has_notifications:
        _emit_notification_bell_once()
```

**4. User-Specific Display**
```python
# From bbsengine6/io/getch.py line 547-548
if result == "KEY_F2" and moniker:
    # Show notifications for THIS user only
    _show_pending_notifications(moniker)
```

## Multi-User Scenario Example

### Setup: Three Users on Same Machine

**User 1 (john)**
```bash
# Logs in from terminal 1
ssh bbs@host
(enters username: john)
```

**User 2 (jane)**
```bash
# Logs in from terminal 2
ssh bbs@host
(enters username: jane)
```

**User 3 (admin)**
```bash
# Logs in from terminal 3
ssh bbs@host
(enters username: admin)
```

### Notifications Fire From Events

```python
# In bbsengine6 code
import bbsengine6.notifyd as notifyd
from datetime import datetime

def on_user_login(user):
    # Fire event with user context
    notifyd.fire_event("user-login", {
        "username": user.moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
```

### Each User Sees Only Their Notifications

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

✅ Each user's `getch()` call checks **ONLY their own queue**
✅ Notifications are **isolated per user**
✅ User identity comes from `_threadlocal.moniker` (thread-local storage)
✅ No cross-user notification leakage
✅ Built-in to bbsengine6 architecture

## How to Use: Multi-User with getch()

### 1. Fire Events with User Context

Always include the user context when firing events:

```python
# bbsengine6/auth.py
import bbsengine6.notifyd as notifyd
from datetime import datetime
from bbsengine6.member import _threadlocal

def on_user_login(user, request):
    # Login logic...
    
    # Fire event - user context already in _threadlocal.moniker
    notifyd.fire_event("user-login", {
        "username": user.moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
```

### 2. Route to User's Queue

In your notification dispatcher:

```python
# bbsengine6/notifyd/__init__.py
import bbsengine6.notify as notify
from bbsengine6.member import _threadlocal

def fire_event(event_name: str, variables: dict) -> None:
    """Fire an event - automatically routes to current user's queue."""
    
    cfg = get_config()
    listeners = cfg.get("event_listeners", {})
    
    if event_name not in listeners:
        return
    
    listener_config = listeners[event_name]
    current_moniker = getattr(_threadlocal, "moniker", None)
    
    if not current_moniker:
        return  # No user context
    
    # Send to THIS user's queue
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

### 3. getch() Displays User-Specific Notifications

No changes needed - getch() already does this:

```python
# In main loop
from bbsengine6.io import getch

while True:
    key = getch.getch_str(timeout=1.0)
    # Automatically checks/displays current user's notifications
    # Bell emits only for THAT user
    # F2 shows only THAT user's notifications
```

## Configuration: Multi-User Setup

### Minimal Config (Same for All Users)

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["john", "jane", "admin"],
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

**Note**: "user" in recipients means "the user who triggered the event" (their moniker)

### Advanced: Different Events for Different Users

```json
{
  "event_listeners": {
    "admin-action": {
      "recipients": ["admin", "audit-team"],
      "template": "admin-action.tmpl",
      "urgency": "high"
    },
    "user-message": {
      "recipients": ["user"],  # Notifies the recipient user
      "template": "message.tmpl",
      "urgency": "medium"
    }
  }
}
```

## Implementation Example: Multi-User BBS

### 1. User Login

```python
# bbsengine6/auth.py
import bbsengine6.notifyd as notifyd
from datetime import datetime

def handle_user_login(username, password, request):
    user = verify_login(username, password)
    
    if not user:
        # Fire failed login event
        notifyd.fire_event("login-failed", {
            "username": username,
            "ip_address": request.remote_addr,
        })
        raise AuthenticationError()
    
    # Fire successful login - goes to user's queue
    notifyd.fire_event("user-login", {
        "username": user.moniker,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
    
    return user
```

### 2. Message Notification

```python
# bbsengine6/messages.py
import bbsengine6.notifyd as notifyd

def send_message(from_user, to_user, text):
    # Save message...
    msg = Message.create(
        from_moniker=from_user.moniker,
        to_moniker=to_user.moniker,
        text=text
    )
    
    # Notify recipient - goes to THEIR queue
    notifyd.fire_event("message-received", {
        "from_user": from_user.moniker,
        "message_preview": text[:50],
        "timestamp": datetime.now().isoformat(),
    })
```

### 3. Admin Actions

```python
# bbsengine6/admin.py
import bbsengine6.notifyd as notifyd

def delete_post(admin_user, post_id):
    post = Post.get(post_id)
    
    # Delete...
    post.delete()
    
    # Notify admin and audit log
    notifyd.fire_event("admin-action", {
        "action": "delete_post",
        "admin": admin_user.moniker,
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
        # 1. Gets current user's moniker from _threadlocal
        # 2. Checks THAT user's notification queue
        # 3. Emits bell only if THAT user has notifications
        # 4. Shows F2 option for THAT user's notifications
        key = getch.getch_str(timeout=1.0)
        
        if key == "Q":
            break
        
        process_key(key)
```

## Comparison: Daemon vs getch() for Multi-User

| Feature | Daemon Model | getch() Model |
|---------|--------------|---------------|
| **Multi-user support** | ❌ Limited (shared config) | ✅ Full (per-user queues) |
| **User isolation** | ❌ No | ✅ Yes |
| **Notifications per user** | ❌ Global queue | ✅ Per-user queue |
| **Privacy** | ❌ Users can see others' notifications | ✅ Only your own |
| **Thread-local integration** | ❌ No | ✅ Yes |
| **Concurrent users** | ⚠️ Works but messy | ✅ Clean design |
| **Implementation** | Complex | Simple |
| **Code changes needed** | Medium | Minimal |

## Recommended Architecture: Multi-User BBS

### Use getch() Integration Because:

1. **✅ Built-in user isolation** - Each user gets their own queue
2. **✅ Thread-local integration** - Moniker from `_threadlocal.moniker`
3. **✅ Simple deployment** - No daemon needed
4. **✅ Scales to multiple users** - Each user's getch() checks their queue
5. **✅ Event-driven** - Fire events with user context
6. **✅ Privacy-respecting** - Users only see their notifications
7. **✅ BBS-friendly** - Notifications during keyboard I/O

### Architecture Diagram

```
User 1 Session          User 2 Session          User 3 Session
    │                       │                       │
    └──→ getch() ─→ Check moniker "john"           │
         bell if john's queue has notifications    │
         │                                          │
         └──→ User 2 getch() ─→ Check moniker "jane"
              bell if jane's queue has notifications
              │
              └──→ User 3 getch() ─→ Check moniker "admin"
                   bell if admin's queue has notifications

Shared config.json (same for all users)
Separate notification queues per user
```

## Migration: Daemon → getch() for Multi-User

If you're currently trying to use daemon for multi-user:

### Step 1: Remove Daemon

```bash
sudo systemctl stop notifyd
sudo systemctl disable notifyd
```

### Step 2: Update Code to Use getch() Integration

```python
# Instead of manually polling or starting daemon:
# Just fire events with user context

notifyd.fire_event("event-name", {
    "username": current_user.moniker,  # Include moniker
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

**getch() integration is superior for multi-user per machine because:**

1. User identity is automatically from `_threadlocal.moniker`
2. bbsengine6.notify already has per-user queues
3. getch() already filters by current user
4. Built-in privacy/isolation
5. No daemon overhead
6. Scales elegantly to multiple concurrent users

**This is the recommended approach for bbsengine6 BBS multi-user support.**

See [GETCH_INTEGRATION.md](GETCH_INTEGRATION.md) for implementation details.
