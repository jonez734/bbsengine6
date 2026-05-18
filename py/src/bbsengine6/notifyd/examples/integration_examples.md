# NotifyD Integration Examples

This document shows how to fire events from bbsengine6 code that will trigger notifications through the notifyd system.

## Overview

The notifyd event system allows bbsengine6 code to trigger notifications by firing events through the event bus. These events can be mapped to custom handlers that send notifications to specified recipients.

## Basic Usage

### 1. Firing a User Login Event

When a user logs in, you can fire a user-login event to notify administrators:

```python
# In bbsengine6/login.py or similar
import bbsengine6.notifyd as notifyd

def handle_user_login(user_id, ip_address):
    # ... normal login logic ...
    
    # Fire notification event
    notifyd.fire_event("user-login", {
        "username": user.username,
        "ip_address": ip_address,
        "timestamp": datetime.now().isoformat(),
    })
```

### 2. Firing a User Logout Event

When a user logs out:

```python
# In bbsengine6/logout.py or similar
import bbsengine6.notifyd as notifyd

def handle_user_logout(user_id, session_duration):
    # ... normal logout logic ...
    
    # Fire notification event
    notifyd.fire_event("user-logout", {
        "username": user.username,
        "timestamp": datetime.now().isoformat(),
        "duration": session_duration,
    })
```

### 3. Firing Custom Events

You can define custom events in your config and fire them from anywhere:

```python
# In any bbsengine6 module
import bbsengine6.notifyd as notifyd

# Security alert event
notifyd.fire_event("security-alert", {
    "alert_type": "suspicious_activity",
    "description": "Multiple failed login attempts detected",
    "ip_address": "192.168.1.100",
    "timestamp": datetime.now().isoformat(),
})

# System maintenance event
notifyd.fire_event("system-maintenance", {
    "task": "Database migration",
    "estimated_duration": "2 hours",
    "start_time": datetime.now().isoformat(),
    "impact": "All users will experience brief downtime",
})
```

## Integration Points

### User Authentication Module

In your user authentication/login module:

```python
# bbsengine6/auth.py
import bbsengine6.notifyd as notifyd
from datetime import datetime

def authenticate_user(username, password, request):
    user = lookup_user(username)
    
    if not user:
        # Log failed attempt
        notifyd.fire_event("user-login-failed", {
            "username": username,
            "ip_address": request.remote_addr,
            "timestamp": datetime.now().isoformat(),
        })
        raise AuthenticationError("Invalid credentials")
    
    if not verify_password(password, user.password_hash):
        notifyd.fire_event("user-login-failed", {
            "username": username,
            "ip_address": request.remote_addr,
            "timestamp": datetime.now().isoformat(),
        })
        raise AuthenticationError("Invalid credentials")
    
    # Successful login
    notifyd.fire_event("user-login", {
        "username": user.username,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
    
    return user
```

### Session Management

Track session activity:

```python
# bbsengine6/session.py
import bbsengine6.notifyd as notifyd
from datetime import datetime

class Session:
    def __init__(self, user, request):
        self.user = user
        self.start_time = datetime.now()
        self.ip_address = request.remote_addr
        
    def close(self):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        notifyd.fire_event("user-logout", {
            "username": self.user.username,
            "timestamp": datetime.now().isoformat(),
            "duration": int(duration),
        })
```

### File Operations

Monitor sensitive file operations:

```python
# bbsengine6/files.py
import bbsengine6.notifyd as notifyd
from datetime import datetime

def delete_sensitive_file(file_path, user):
    # Check permissions
    if not user.has_permission("delete_files"):
        notifyd.fire_event("unauthorized-action", {
            "action": "delete_file",
            "file": file_path,
            "user": user.username,
            "timestamp": datetime.now().isoformat(),
        })
        raise PermissionError("Not allowed to delete files")
    
    # Perform deletion
    os.remove(file_path)
    
    # Log the operation
    notifyd.fire_event("file-deleted", {
        "file_path": file_path,
        "user": user.username,
        "timestamp": datetime.now().isoformat(),
    })
```

### Error Handling

Notify on critical errors:

```python
# bbsengine6/error_handler.py
import bbsengine6.notifyd as notifyd
from datetime import datetime
import traceback

def handle_critical_error(error, request=None):
    notifyd.fire_event("critical-error", {
        "error_type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
        "timestamp": datetime.now().isoformat(),
        "request_url": request.url if request else None,
    })
```

## Configuration

To enable these events, add them to your notifyd config:

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["admin@example.com", "security@example.com"],
      "template": "user-login.tmpl",
      "urgency": "high"
    },
    "user-logout": {
      "recipients": ["admin@example.com"],
      "template": "user-logout.tmpl",
      "urgency": "medium"
    },
    "user-login-failed": {
      "recipients": ["security@example.com"],
      "template": "login-failed.tmpl",
      "urgency": "high"
    },
    "security-alert": {
      "recipients": ["security-team@example.com"],
      "template": "security-alert.tmpl",
      "urgency": "critical"
    },
    "file-deleted": {
      "recipients": ["audit-log@example.com"],
      "template": "file-deleted.tmpl",
      "urgency": "medium"
    }
  }
}
```

## Template Variables

Template variables are passed as a dictionary to `fire_event()`. In your templates, use `{variable_name}` syntax:

### user-login.tmpl
- `{username}` - The username that logged in
- `{ip_address}` - Client IP address
- `{timestamp}` - Login timestamp

### user-logout.tmpl
- `{username}` - The username that logged out
- `{timestamp}` - Logout timestamp
- `{duration}` - Session duration in seconds

### Custom Templates

Create template files in `templates/` directory:

```
# templates/custom-event.tmpl
Custom Event Notification

User: {username}
Event Type: {event_type}
Details: {details}
Timestamp: {timestamp}
```

Then reference in config:

```json
{
  "event_listeners": {
    "custom-event": {
      "recipients": ["team@example.com"],
      "template": "custom-event.tmpl",
      "urgency": "high"
    }
  }
}
```

## Error Handling in Events

The notifyd event system handles errors gracefully:

```python
# Even if the event fires fails, your code continues
try:
    notifyd.fire_event("important-event", {
        "data": "value"
    })
except Exception as e:
    # Log but don't crash
    logger.warning(f"Failed to fire event: {e}")
```

## Thread Safety

Events are fired asynchronously in background threads, so your main code doesn't block:

```python
# This returns immediately, even if notification sending takes time
notifyd.fire_event("user-login", {...})

# Your code continues immediately
next_operation()
```

## Testing Events

Use the CLI to test your event configuration:

```bash
# Test that notifyd can connect to IMAP servers
python -m bbsengine6.notifyd test-imap

# Test that notifications send correctly
python -m bbsengine6.notifyd test-notify

# Check event configuration
python -m bbsengine6.notifyd status
```

See the main README for more details on CLI commands.
