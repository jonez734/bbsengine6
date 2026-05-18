# bbsengine6 notifyd - Database Schema

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Database Schema

### Tables

#### notifyd_imap_state

Tracks last processed email UID per server/mailbox to avoid duplicates.

```sql
CREATE TABLE IF NOT EXISTS notifyd_imap_state (
    id SERIAL PRIMARY KEY,
    server VARCHAR(255) NOT NULL,
    mailbox VARCHAR(255) NOT NULL,
    max_uid INTEGER DEFAULT 0,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server, mailbox)
);

CREATE INDEX IF NOT EXISTS idx_notifyd_imap_state_server 
  ON notifyd_imap_state(server, mailbox);
```

**Purpose**: Prevent duplicate email notifications by tracking the last UID processed for each server/mailbox combination.

**Columns**:
- `id`: Primary key
- `server`: IMAP server name (from config)
- `mailbox`: Mailbox name (e.g., "INBOX")
- `max_uid`: Last processed email UID
- `last_checked`: Timestamp of last check
- `updated_at`: Last update timestamp

#### notifyd_history

Audit log of all notifications sent by notifyd.

```sql
CREATE TABLE IF NOT EXISTS notifyd_history (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(255) NOT NULL,
    recipients TEXT[] DEFAULT ARRAY[]::TEXT[],
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_id INTEGER,
    data JSONB,
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_notifyd_history_type 
  ON notifyd_history(notification_type);

CREATE INDEX IF NOT EXISTS idx_notifyd_history_sent_at 
  ON notifyd_history(sent_at DESC);
```

**Purpose**: Complete audit trail of all notifications sent by the notifyd system.

**Columns**:
- `id`: Primary key
- `notification_type`: Type (e.g., "imap.message", "user.login")
- `recipients`: List of recipients
- `sent_at`: When notification was sent
- `notification_id`: ID returned by notify.send()
- `data`: Template variables (JSONB)
- `status`: "sent", "failed", or "pending"
- `error_message`: Error details if status="failed"

---

## Storage Layer API

### NotificationStorage Class

```python
class NotificationStorage:
    def __init__(self, pool: ConnectionPool, dbname: str = "bbsengine6"):
        """Initialize storage with existing connection pool"""
        self.pool = pool
        self._ensure_schema()
    
    def get_last_uid(self, server: str, mailbox: str) -> int:
        """Get last processed email UID for server/mailbox"""
        # Returns last max_uid or 0 if none
    
    def set_last_uid(self, server: str, mailbox: str, uid: int):
        """Update last processed UID (UPSERT)"""
        # Inserts or updates depending on existing record
    
    def record_notification(self,
                           notification_type: str,
                           recipients: List[str],
                           template_vars: dict,
                           notification_id: Optional[int] = None,
                           status: str = "sent"):
        """Record sent notification in history"""
        # Records to notifyd_history table
    
    def get_notification_history(self, limit: int = 100) -> List[dict]:
        """Get recent notifications sent by notifyd"""
        # Returns last N notifications
```

---

## State Tracking

### IMAP UID Tracking

When polling IMAP servers, notifyd tracks the last UID processed to avoid sending duplicate notifications:

```python
# On first poll of a server/mailbox
storage.get_last_uid("Gmail", "INBOX")  # Returns 0 (none yet)

# After processing email with UID 100
storage.set_last_uid("Gmail", "INBOX", 100)

# Next poll only fetches UIDs > 100
new_uids = imap_client.search(f"UID {100+1}:*")
```

### Notification History

Every notification sent is recorded in the history table:

```python
storage.record_notification(
    notification_type="imap.message",
    recipients=["player1", "player2"],
    template_vars={
        "sender": "user@gmail.com",
        "subject": "Hello",
        "body": "Message text"
    },
    notification_id=12345,
    status="sent"
)
```

---

## Integration with bbsengine6

### Connection Pool

notifyd uses bbsengine6's existing database connection pool:

```python
from bbsengine6.database import getpool

pool = getpool()  # Get existing pool
storage = NotificationStorage(pool)  # Use for notifyd state tracking
```

### notification Table Integration

Notifications are sent through bbsengine6.notify, which records to `engine.__notify`:

```python
import bbsengine6.notify as notify

# Call notify.send() which handles all recipient routing
notify.send(
    recipients=["player1", "player2"],
    message="Email from Gmail",
    template="imap-message.tmpl",
    urgency="ROUTINE"
)
# Records to engine.__notify table
```

---

## Performance

### Indexes

Indexes are created on:
- `notifyd_imap_state(server, mailbox)` - For UID lookups
- `notifyd_history(notification_type)` - For filtering by type
- `notifyd_history(sent_at DESC)` - For recent history queries

### Query Performance

- **UID lookup**: O(1) via index
- **Set UID**: O(1) UPSERT
- **Record notification**: O(1) INSERT
- **History query**: O(n) with limit, good performance

---

## Maintenance

### Schema Initialization

The schema is automatically created on daemon startup:

```python
daemon.start()  # Calls storage._ensure_schema()
```

### Cleanup

Historical data can be cleaned up manually:

```sql
-- Delete notifications older than 30 days
DELETE FROM notifyd_history 
WHERE sent_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
```

### Monitoring

Check database size:

```sql
SELECT 
    pg_size_pretty(pg_total_relation_size('notifyd_imap_state')) as imap_size,
    pg_size_pretty(pg_total_relation_size('notifyd_history')) as history_size;
```

---

For configuration details, see [BBSENGINE6_NOTIFYD_CONFIGURATION.md](BBSENGINE6_NOTIFYD_CONFIGURATION.md).

For component details, see [BBSENGINE6_NOTIFYD_COMPONENTS.md](BBSENGINE6_NOTIFYD_COMPONENTS.md).
