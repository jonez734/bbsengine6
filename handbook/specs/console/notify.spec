# Notification System Module (notify.py)

## Overview

`notify.py` manages system notifications and notification preferences. **Status: Stub implementation** — Core database schema exists but interface is incomplete.

**File:** `bbsengine6/console/notify.py`  
**Size:** 25 lines  
**Status:** Incomplete — designed for extensibility

---

## Standard Module Interface (Declared)

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

All functions are declared but minimally implemented.

---

## Current Implementation

### init()

```python
def init(args, **kwargs) -> bool:
    return True
```

Stub — no initialization needed currently.

---

### access()

```python
def access(args, op, **kwargs) -> bool:
    return True
```

Stub — no access restrictions defined yet.

---

### buildargs()

```python
def buildargs(args, **kwargs) -> ArgumentParser | None:
    return None
```

Stub — no CLI interface implemented.

---

### main()

```python
def main(args, **kwargs) -> bool:
    return True
```

Stub — core logic not yet implemented.

---

## Intended Design

Based on database schema and module naming, notify.py is intended to provide:

### Notification Management

1. **View notifications** — Display system notifications
2. **Mark read/unread** — Update notification status
3. **Manage preferences** — Configure notification types to receive
4. **Clear old notifications** — Archive/delete old records

### Menu Interface (Proposed)

```
Notifications
=============

[N]ew            - View new notifications
[A]ll            - View all notifications
[P]references    - Set notification preferences
[C]lear          - Clear old notifications
[X]it            - Return to main menu
```

### Operations (Proposed)

**Display Notifications:**
```python
SELECT * FROM engine.notification 
WHERE memberid = current_member_id
ORDER BY created DESC
LIMIT 50
```

**Mark as Read:**
```python
UPDATE engine.notification 
SET read = TRUE 
WHERE notificationid = %s
```

**Set Preferences:**
```python
UPDATE engine.subscription 
SET enabled = %s 
WHERE memberid = %s AND notificationtype = %s
```

---

## Database Schema

### engine.notification

Stores notification records:

| Column | Type | Purpose |
|--------|------|---------|
| `notificationid` | serial | Primary key |
| `memberid` | int | Recipient (FK to engine.member) |
| `notificationType` | varchar | Type of notification |
| `subject` | varchar | Notification title |
| `message` | text | Notification body |
| `created` | timestamp | When notification was created |
| `read` | boolean | Whether member has read it |
| `readdate` | timestamp | When member read it (NULL if unread) |

### engine.notification_type

Defines available notification types:

| Column | Type | Purpose |
|--------|------|---------|
| `notificationtypeid` | varchar | Type identifier (e.g., "NEWMESSAGE") |
| `description` | varchar | Human-readable name |
| `defaultenabled` | boolean | Enabled by default for new members |

### engine.subscription

Member notification preferences:

| Column | Type | Purpose |
|--------|------|---------|
| `subscriptionid` | serial | Primary key |
| `memberid` | int | Member (FK to engine.member) |
| `notificationtypeid` | varchar | FK to notification_type |
| `enabled` | boolean | Whether member receives this type |

---

## Standard Notification Types (Proposed)

```
NEWMESSAGE      - New message received
NEWMAIL         - New email received
NEWMEETING      - New meeting scheduled
GROUPMENTION    - Mentioned in group chat
FORUMREPLY      - Reply to your forum post
CREDITSADDED    - Credits added to account
EVENTNOTICE     - System event notification
MAINTENANCE     - System maintenance notice
```

---

## Implementation Approach

### Phase 1 (Current)

- Stub module exists
- Module discoverable by console
- No actual functionality

### Phase 2 (Proposed)

- Display notifications interface
- Mark read/unread
- Basic preferences editor
- Database schema verified in checknotify.py

### Phase 3 (Proposed)

- Background notification generator (in other modules)
- Email notification integration
- Notification history/archives
- Advanced filtering and search

---

## Integration Points

**Current Integration:**
- Module discovered by `lib.discover_console_modules()`
- Added to main menu on startup
- Available as `zoidoffice notify` subcommand

**Future Integration:**
- Other modules call: `notify.send(memberid, type, subject, body)`
- Session activity triggers notifications
- Member actions trigger notifications

---

## Error Handling

**Current (Stub):**
- Always returns True (no operations to fail)

**Proposed:**
- Database connection errors → logged, return False
- Member not found → error message, return False
- Invalid notification type → error message, return False
- Preference update fails → rollback, return False

---

## Dependencies

**Current:**
- None (stub implementation)

**Proposed:**
- `bbsengine6.database` — Database connection and queries
- `bbsengine6.member` — Member lookup
- `bbsengine6.io` — Input/output
- `bbsengine6.util` — Utility functions

---

## Future Enhancements

### Notification Delivery Channels

- In-app notifications (current schema)
- Email notifications (integration with email.py)
- SMS notifications (future)
- Push notifications (future)

### Notification Triggers

- New message alert
- New post reply
- Group mentions
- Credit additions
- System events
- Maintenance notices

### Notification Management

- Bulk mark as read
- Notification archives
- Search notifications
- Export notification history
- Notification statistics

### Preferences

- Per-notification-type enable/disable
- Quiet hours (no notifications during time period)
- Delivery method preferences
- Digest mode (daily/weekly summary)

