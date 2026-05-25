# NotifyD Multi-User Guide

**See Also**: [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](../../BBSENGINE6_NOTIFYD_DEPLOYMENT.md#multi-user-considerations) for comprehensive deployment guidance

## Current Design: Single System Daemon

NotifyD is designed as a **single system-wide daemon** that runs as the `bbsengine6` system user. It is **not a multi-user system** in the sense that each bbsengine6 application user gets their own daemon instance.

**Important**: NotifyD monitors email accounts and fires application-level events, not user-level sessions. It's designed to be a notification infrastructure for the bbsengine6 application as a whole.

## What Works: Multiple Email Accounts & Recipients

Even though there's only one daemon, you can handle multiple email accounts and notify multiple people:

### Multiple Email Servers

One daemon monitors multiple email accounts simultaneously:

```json
{
  "imap_servers": [
    {
      "name": "Admin Email",
      "host": "imap.gmail.com",
      "port": 993,
      "ssl": true,
      "username": "admin@company.com",
      "password": "${ADMIN_EMAIL_PASSWORD}",
      "mailboxes": ["INBOX"],
      "poll_interval": 60
    },
    {
      "name": "Support Email",
      "host": "imap.company.com",
      "port": 993,
      "ssl": true,
      "username": "support@company.com",
      "password": "${SUPPORT_EMAIL_PASSWORD}",
      "mailboxes": ["INBOX", "Escalations"],
      "poll_interval": 120
    },
    {
      "name": "Alerts Email",
      "host": "imap.alerts.example.com",
      "port": 993,
      "ssl": true,
      "username": "alerts@example.com",
      "password": "${ALERTS_EMAIL_PASSWORD}",
      "mailboxes": ["INBOX"],
      "poll_interval": 30
    }
  ]
}
```

Each email account's messages will trigger IMAP notifications to configured recipients.

### Multiple Recipients Per Event

Events can be sent to multiple people:

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": [
        "admin@company.com",
        "security@company.com",
        "audit@company.com"
      ],
      "template": "user-login.tmpl",
      "urgency": "high"
    },
    "critical-error": {
      "recipients": [
        "dev-team@company.com",
        "ops-team@company.com",
        "management@company.com"
      ],
      "template": "critical-error.tmpl",
      "urgency": "critical"
    }
  }
}
```

### Different Events for Different Groups

Create event listeners that target different teams:

```json
{
  "event_listeners": {
    "user-login": {
      "recipients": ["security-team@company.com"],
      "template": "user-login.tmpl",
      "urgency": "high"
    },
    "database-error": {
      "recipients": ["database-admins@company.com"],
      "template": "db-error.tmpl",
      "urgency": "critical"
    },
    "file-upload": {
      "recipients": ["audit-log@company.com"],
      "template": "file-upload.tmpl",
      "urgency": "medium"
    },
    "payment-processed": {
      "recipients": ["accounting@company.com"],
      "template": "payment.tmpl",
      "urgency": "high"
    }
  }
}
```

## Current Limitations

### 1. Single Daemon Instance

- Only one notifyd process runs per machine
- All events and emails are processed by the same daemon
- Cannot run separate instances for different application users

### 2. Shared Configuration

- One config file at `/etc/bbsengine6/notifyd.json`
- All application users share the same IMAP servers and event listeners
- No per-user customization of which events to monitor

**Workaround**: Use event filtering in templates or pre-processing:

```python
# In your bbsengine6 code
import bbsengine6.notifyd as notifyd

# Include user context in event
notifyd.fire_event("file-deleted", {
    "file_path": "/data/important.txt",
    "user": current_user.username,  # Include user context
    "timestamp": datetime.now().isoformat(),
})
```

Then in the template (file-deleted.tmpl):
```
File Deleted Alert

User: {user}
File: {file_path}
Time: {timestamp}

This deletion was performed by: {user}
```

### 3. Shared Notification History

- All notifications logged to single `bbsengine6.notification_log` table
- No per-user privacy isolation
- All daemon activity visible to anyone with database access

**Workaround**: Add user field to events and filter in application code:

```python
from bbsengine6.notifyd import storage
from bbsengine6.database import pool

# Get notifications for specific user
with pool.connection() as conn:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT * FROM bbsengine6.notification_log
            WHERE template_vars->>'user' = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (username,))
        user_notifications = cur.fetchall()
```

### 4. No User-Specific Email Monitoring

- Cannot assign specific email accounts to specific application users
- One user's email alerts go to all configured recipients
- All IMAP servers monitored by the same daemon

**Workaround**: Use different email account names in config to distinguish sources:

```json
{
  "imap_servers": [
    {
      "name": "john_doe_email",
      "host": "imap.gmail.com",
      "username": "john.doe@company.com",
      "password": "${JOHN_EMAIL_PASSWORD}",
      "mailboxes": ["INBOX"]
    },
    {
      "name": "jane_smith_email",
      "host": "imap.gmail.com",
      "username": "jane.smith@company.com",
      "password": "${JANE_EMAIL_PASSWORD}",
      "mailboxes": ["INBOX"]
    }
  ]
}
```

Then in template variable building (notification.py would need enhancement):
```python
# When creating notification from IMAP email
notify_data = {
    "sender": sender,
    "subject": subject,
    "body": body,
    "server": "john_doe_email",  # Include which account
    "user": "john.doe"  # Derived from account name
}
```

### 5. Event Isolation

- Any bbsengine6 code can fire any event
- No permission checking on who can fire what events
- All fired events go to all configured listeners

**Workaround**: Implement authorization in code before firing events:

```python
import bbsengine6.notifyd as notifyd

def delete_file(file_path, current_user):
    # Check permission
    if not current_user.has_permission("delete_files"):
        # Fire unauthorized event (different recipients)
        notifyd.fire_event("unauthorized-action", {
            "action": "delete_file",
            "file": file_path,
            "user": current_user.username,
            "ip_address": request.remote_addr,
            "timestamp": datetime.now().isoformat(),
        })
        raise PermissionError("Not allowed to delete files")
    
    # Perform deletion
    os.remove(file_path)
    
    # Fire authorized event
    notifyd.fire_event("file-deleted", {
        "file_path": file_path,
        "user": current_user.username,
        "timestamp": datetime.now().isoformat(),
    })
```

## Workaround Patterns

### Pattern 1: Include User Context in Events

Always include `user` field in event data:

```python
import bbsengine6.notifyd as notifyd
from datetime import datetime

def on_user_login(user, request):
    notifyd.fire_event("user-login", {
        "username": user.username,
        "user_id": user.id,
        "ip_address": request.remote_addr,
        "timestamp": datetime.now().isoformat(),
    })
```

Then filter in templates or downstream processing:
```
User Login: {username}
User ID: {user_id}
IP: {ip_address}
Time: {timestamp}
```

### Pattern 2: Event Type Namespacing

Use event names to distinguish user contexts:

```python
# Instead of generic "file-deleted" for all users
# Use specific event types that imply the context

# For operations by admin user
notifyd.fire_event("admin-file-deleted", {...})

# For operations by regular users
notifyd.fire_event("user-file-deleted", {...})

# For operations by system user
notifyd.fire_event("system-file-deleted", {...})
```

Config example:
```json
{
  "event_listeners": {
    "admin-file-deleted": {
      "recipients": ["security@company.com", "audit@company.com"],
      "template": "admin-file-deleted.tmpl",
      "urgency": "high"
    },
    "user-file-deleted": {
      "recipients": ["audit@company.com"],
      "template": "user-file-deleted.tmpl",
      "urgency": "medium"
    }
  }
}
```

### Pattern 3: Conditional Recipients Based on Content

Use event data to determine recipients in application code:

```python
import bbsengine6.notifyd as notifyd
from bbsengine6.notifyd import notification

# Fire generic event
event_data = {
    "severity": "critical",
    "user": current_user.username,
    "description": error_message,
}
notifyd.fire_event("application-error", event_data)

# In notification dispatcher, route based on severity:
# (Would require modifying notification.py)
if event_data.get("severity") == "critical":
    recipients = ["cto@company.com", "ops@company.com"]
elif event_data.get("severity") == "warning":
    recipients = ["ops@company.com"]
else:
    recipients = ["dev@company.com"]
```

### Pattern 4: Store User Context in Event History

Query events by user from notification log:

```python
from bbsengine6.notifyd import storage
from bbsengine6.database import pool

def get_user_notification_history(username, days=30):
    """Get all notifications related to a specific user."""
    history = storage.get_notification_history(
        days=days,
        event_type=None
    )
    
    # Filter to events involving this user
    user_events = [
        event for event in history
        if event.get("template_vars", {}).get("user") == username
    ]
    
    return user_events
```

## Recommendations

### For Single-User Deployments

If notifyd monitors email for a single person/team, the current design works well:

1. Configure all IMAP servers in config
2. Set recipient list to the appropriate people
3. Use event types to categorize notifications

### For Multi-User Scenarios (Same Machine)

Use these patterns:

1. **Always include user context**: Every event should have `{user}` field
2. **Use event type namespacing**: Different event types for different user classes
3. **Document configuration**: Make it clear which emails/events go to whom
4. **Filter in application code**: Implement authorization checks before firing events
5. **Query history by user**: Use notification log queries to audit per-user activity

### For Multi-User Scenarios (Different Machines)

If you need completely isolated daemon instances per user:

1. Run separate notifyd instances on different machines
2. Each instance has its own config file
3. Each instance monitors its own IMAP servers
4. Events are isolated by machine/instance

## Future Enhancements

If strict multi-user isolation becomes necessary, potential future improvements could include:

### Option 1: User Context in Configuration

```json
{
  "users": {
    "john.doe": {
      "imap_servers": [...],
      "event_listeners": {...}
    },
    "jane.smith": {
      "imap_servers": [...],
      "event_listeners": {...}
    }
  }
}
```

### Option 2: Multi-Instance Systemd Service

```bash
# Template service file
/etc/systemd/system/notifyd@.service

# Enable per-user instances
systemctl start notifyd@john.doe
systemctl start notifyd@jane.smith
```

### Option 3: Daemon-Level User Filtering

Add authorization checks in the daemon itself:
```python
# Before firing event
if not check_user_permission(event_name, current_user):
    raise PermissionError(f"User {current_user} cannot fire {event_name}")
```

## Summary

**NotifyD's Current Design**:
- Single system daemon
- Multiple email accounts
- Multiple recipients per event
- Shared notification history
- No per-user isolation

**Best For**:
- Monitoring multiple email accounts for a single team
- Broadcasting notifications to appropriate recipients
- System-level event notification

**Workarounds for Multi-User**:
- Include user context in event data
- Use event type namespacing
- Filter notifications by user in application code
- Query notification log by user field
- Implement authorization checks before firing events

**Not Suitable For**:
- Strict user-level privacy requirements
- Completely isolated per-user event monitoring
- User-specific email account management
- Per-user configuration

See [Integration Examples](examples/integration_examples.md) for code patterns that work with the current design.
