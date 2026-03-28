# Testing the Notification System

This guide shows how to test sending and receiving notifications.

## Prerequisites

- PostgreSQL database running
- bbsengine6 database initialized with notify schema
- Test users: `jam`, `alice`, `bob` created in `engine.__member` table

## Running Tests

### Unit Tests (No Database Required)

Test validation, data structures, and queue operations:

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest tests/test_notify.py -v
```

**Result:** 37 tests, all passing
- Enum values
- Dataclass operations
- Queue operations
- Template validation and rendering
- Variable validation
- Moniker validation

### Integration Tests (Requires Database)

Test sending, receiving, and managing notifications with a real database:

```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest tests/test_notify_integration.py -v -s
```

**The `-s` flag shows print output from the tests**

## Test Classes

### 1. TestNotificationSendAndReceive
Examples of basic notification sending:
- `test_send_simple_notification()` - Send basic notification
- `test_send_with_urgency()` - Send with ROUTINE/URGENT/CRITICAL
- `test_send_with_data()` - Include structured data
- `test_send_to_multiple_recipients()` - Send to multiple users

### 2. TestNotificationGroups
Group-based targeting:
- `test_create_and_use_group()` - Create group and send to members
- `test_add_remove_group_members()` - Manage group membership

### 3. TestNotificationBlocking
One-way blocking:
- `test_block_sender()` - User blocks another user's notifications
- `test_unblock_sender()` - Remove block

### 4. TestNotificationRetrieval
Receiving and consuming notifications:
- `test_get_notifications_from_db()` - Retrieve from database
- `test_get_unread_notifications()` - Get only unread
- `test_get_urgent_notifications()` - Get high-priority notifications

### 5. TestNotificationQueue
Real-time in-memory queues:
- `test_notification_queue_basic()` - Queue for active sessions
- `test_queue_urgent_check()` - Check for urgent notifications

### 6. TestNotificationTypes
Type management:
- `test_register_type_with_settings()` - Register custom type
- `test_get_all_types()` - List all types

### 7. TestRateLimiting
Rate limit enforcement:
- `test_rate_limit_concept()` - Understanding limits

### 8. TestCompleteWorkflow
End-to-end examples:
- `test_complete_notification_workflow()` - Full send→receive→read flow
- `test_social_notification_example()` - Real-world social feature
- `test_game_victory_example()` - Real-world game notification

## Quick Start: Manual Testing

### 1. Import and Initialize

```python
from bbsengine6 import notify

# Register a notification type
notify.register_type(
    type_name="HELLO",
    default_urgency=notify.NotificationUrgency.ROUTINE,
    max_per_hour=100
)
```

### 2. Send a Notification

```python
result = notify.send(
    notification_type="HELLO",
    recipients=["jam"],
    template="Hello {name}!",
    template_vars={"name": "Jam"}
)

print(f"Sent: {result.message}")
# Output: Sent: Hello Jam!
```

### 3. Receive Notifications

```python
# Get all notifications
notifications = notify.get_notifications("jam", limit=10)
print(f"Found {len(notifications)} notifications")

# Get unread only
unread = notify.get_notifications("jam", unread_only=True)
print(f"Unread: {len(unread)}")

# Get urgent/critical
urgent = notify.get_urgent("jam")
print(f"Urgent: {len(urgent)}")
```

### 4. Mark as Read

```python
notify.mark_read(notification_id=1, moniker="jam")
```

### 5. Use Groups

```python
# Create group
notify.create_group("@guild:dragons", ["jam", "alice", "bob"])

# Send to group
notify.send(
    notification_type="HELLO",
    recipients=["@guild:dragons"],
    template="Guild announcement!"
)
```

### 6. Block Users

```python
# Block alice from sending to jam
notify.block("jam", "alice")

# Check if blocked
is_blocked = notify.is_blocked("alice", "jam")
print(f"Blocked: {is_blocked}")

# Get all blockers of jam
blockers = notify.get_blocked("jam")
print(f"Jam is blocked by: {blockers}")

# Unblock
notify.unblock("jam", "alice")
```

## What Gets Stored in Database

### Core Tables
- `engine.__notify` - All notifications sent
- `engine.__notify_recipient` - Per-user delivery/read status
- `engine.__notify_block` - Blocking relationships
- `engine.__notify_group` - Group memberships
- `engine.__notify_type` - Registered types and rate limits
- `engine.__notify_rate_limit` - Rate limit tracking

### Views (for queries)
- `engine.notify` - Main join view
- `engine.notify_unread` - Unread notifications only
- `engine.notify_urgent` - Urgent/critical only
- `engine.notify_blocked` - Blocked notifications (audit)

## Example SQL Queries

### Check unread notifications for user
```sql
SELECT * FROM engine.notify_unread 
WHERE recipient_moniker = 'jam'
ORDER BY datecreated DESC;
```

### Check blocking relationships
```sql
SELECT sender_moniker FROM engine.__notify_block 
WHERE blocker_moniker = 'jam';
```

### Check rate limit capacity
```sql
SELECT 
    nt.type_name,
    nrl.send_count,
    nt.max_per_user_per_hour,
    (nt.max_per_user_per_hour - nrl.send_count) as remaining
FROM engine.__notify_rate_limit nrl
JOIN engine.__notify_type nt ON nrl.notification_type = nt.type_name
WHERE nrl.sender_moniker = 'jam'
  AND (now() - nrl.window_start) < interval '1 hour';
```

## Troubleshooting

### "Invalid moniker" error
- Check that user exists in `engine.__member` table
- Monikers are case-sensitive

### "Group does not exist" error
- Check group was created with `create_group()`
- Group names are case-sensitive and must be exact

### "Rate limit exceeded" error
- Type has too many notifications sent in last hour
- Check `__notify_type.max_per_user_per_hour`
- Adjust with `set_rate_limit()` or wait for window to expire

### Database connection errors
- Ensure PostgreSQL is running
- Check bbsengine6 database exists
- Run schema initialization if needed

## Next Steps

1. Run unit tests: `pytest tests/test_notify.py -v`
2. Run integration tests: `pytest tests/test_notify_integration.py -v -s`
3. Try manual examples in Python REPL
4. Integrate into your application code
5. Create notifications for real application events
