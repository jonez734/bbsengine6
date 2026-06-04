# BBSEngine6 Notify Module Specification

## Overview

The `bbsengine6.notify` module provides a user notification system with templating, rate limiting, blocking support, and (optionally) tamper-proof message authentication.

## Architecture

```
Application
    │
    ├── send() ──→ Database (__notify, __notify_recipient, __notify_type,
    │                      __notify_group, __notify_group_member,
    │                      __notify_block)
    │
    ├── get_notifications() ──→ Database ──→ Notification[]
    │
    ├── UserNotificationQueue (in-process, per-moniker queue)
    │
    └── Daemon (background worker for email/TUI delivery)
```

## Database Schema

### `engine.__notify`
| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| notification_type | citext | Type name (e.g. `social_mention`) |
| sender_moniker | citext FK | Who sent it (nullable) |
| template | citext | Template string or raw message |
| template_vars | jsonb | Variables for template expansion |
| rendered_message | text | Final rendered message |
| data | jsonb | Arbitrary structured data |
| urgency | text | CRITICAL, URGENT, IMPORTANT, ROUTINE |
| should_persist | boolean | Whether to store in DB |
| mac | text | HMAC-SHA256 of immutable content (optional) |
| datecreated | timestamptz | Creation timestamp |

### `engine.__notify_recipient`
Links notifications to recipients, tracks read/delivered state.

### `engine.__notify_type`
Type registry with per-type default urgency and rate limits.

### `engine.__notify_block`
Sender → recipient blocklist.

### `engine.__notify_group`
Named groups of recipients.

### `engine.__notify_group_member`
Group membership.

## Tamper-Proof Messaging (HMAC)

Notifications can be protected against tampering at rest using HMAC-SHA256. This is independent of `bbsengine6.net` transport security — it protects local DB storage.

### Enabling

The HMAC key is read from (priority order):

1. `BBSENGINE6_NOTIFY_MAC_KEY` environment variable
2. `/etc/bbsengine6/notify.key` file (0600 permissions, root-only readable)

Generate and install a production key:

```bash
make -f Makefile.notify-key install-system KEY_DIR=/etc/bbsengine6
```

Or generate locally:

```bash
make -f Makefile.notify-key gen-key KEY_DIR=$HOME/.config/bbsengine6
```

The key must be stable — if it changes, existing notifications will fail verification.

### Protected Fields

The MAC is computed over these immutable notification fields:

```
notification_type | sender_moniker | template | template_vars_json |
rendered_message | data_json | urgency
```

Changes to any of these fields after `send()` will cause `get_notifications()` to raise `NotificationTamperError`.

### DB Migration

The `mac` column must exist in `__notify`. Add it with:

```sql
ALTER TABLE engine.__notify ADD COLUMN mac text;
```

Or let the application auto-detect it. The code probes `information_schema.columns` to determine column existence, so no migration is strictly required for the application to function — notifications will simply be stored and verified without MAC protection.

### Backwards Compatibility

- No key configured (env var or file): MAC column is unused, notifications work normally.
- Old DB without `mac` column: `send()` omits the column, `get_notifications()` skips verification.
- New DB with `mac` column: MAC is computed and stored on `send()`, verified on `get_notifications()`.

## Public API

```python
from bbsengine6.notify import (
    send,                    # Create and send a notification
    get_notifications,       # Retrieve notifications for a user
    mark_read,               # Mark notification as read
    mark_delivered,          # Mark notification as delivered
    expunge,                 # Delete a notification (sender only)
    register_type,           # Register a notification type with rate limits
    count,                   # Count unread notifications
    get_urgent,              # Get CRITICAL/URGENT notifications
    block,                   # Block a sender
    unblock,                 # Unblock a sender
    is_blocked,              # Check if sender is blocked
    get_blocked,             # List blocked senders
    create_group,            # Create a recipient group
    add_to_group,            # Add member to group
    get_group_members,        # List group members
    remove_from_group,        # Remove member from group
    get_queue,               # Get in-process notification queue for a user
    is_enabled,              # Check if notify subsystem is enabled
    enable,                  # Enable the notify subsystem
    disable,                 # Disable the notify subsystem (count returns 0)
    NotificationUrgency,     # CRITICAL, URGENT, IMPORTANT, ROUTINE
    Notification,            # Notification dataclass
    NotificationTamperError, # Raised when HMAC verification fails
)
```

## Subsystem Toggle

The notify subsystem can be disabled at runtime to skip DB access entirely:

```python
from bbsengine6 import notify

notify.disable()  # count() now returns 0, no DB connections
# ... do work without notify overhead ...
notify.enable()   # re-enable
```

`count()` uses `autocommit=True` for its read-only SELECT COUNT query,
eliminating "rolling back returned connection [INTRANS]" warnings from
psycopg_pool when the connection is returned to the pool.

### Connection Resolution

Most notify API calls (`count`, `get_notifications`, `mark_read`, ...) accept
the following kwargs for database access, resolved in this priority order
by `_resolve_conn()`:

1. `conn=` — use the caller's existing connection
2. `pool=` — borrow a connection from the caller's pool
3. `args=` — build/cache a pool via `database.getpool(args)`, which uses
   `args.databasename`, `args.databasehost`, `args.databaseport`,
   `args.databaseuser`, `args.databasepassword`
4. **Fallback** — `getpool(args=None, dbname=_default_db())` where
   `_default_db()` reads the `BBSENGINE6_DBNAME` env var (default
   `bbsengine6`). This path uses no host, so libpq attempts a UNIX socket
   connection.

Callers should always pass `args=args` (or an explicit `pool=`/`conn=`)
to avoid the fallback. The fallback exists only for last-resort/legacy
code paths and will fail loudly when the default database does not exist
or the UNIX socket is unreachable.

## Rate Limiting

Per-sender, per-type rate limits are enforced at `send()` time. Default is 20 per hour per type. The `set_rate_limit()` function overrides limits.

## Delivery

- **Database**: All notifications with `should_persist=True` are stored.
- **In-process queue**: `UserNotificationQueue` holds unsent notifications per-moniker.
- **Daemon**: Background `notifyd` reads queues and delivers via TUI/email.
