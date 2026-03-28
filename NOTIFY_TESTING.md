# Testing the Notification System

This guide shows how to test sending and receiving notifications.

## Prerequisites

- PostgreSQL database running with oidentd authentication
- Test database `zoid6test` (will be created if it doesn't exist)
- `opencode` PostgreSQL user (oidentd auth, no password needed)
- Engine schema and member table already initialized in `zoid6test`

## Automatic Database Setup

**Good news!** Tests automatically initialize the notify schema on first run. You don't need to manually set up anything beyond the prerequisites above.

**How it works:**
1. Pytest fixtures in `conftest.py` run before tests
2. Database connection established to `zoid6test` as `opencode` user
3. 7 notify-specific SQL files loaded (skip if already exist)
4. Test users `alice` and `bob` created (skip if already exist)
5. Each test runs in its own transaction (rolled back after test)

**First Run:**
```bash
cd /home/opencode/data/work/bbsengine6/py
source /home/opencode/.venv/bin/activate
BBSENGINE6_DBNAME=zoid6test python -m pytest tests/test_notify_integration.py -v -s
```

**Subsequent Runs:**
```bash
# Same command - tables already exist, tests run faster
BBSENGINE6_DBNAME=zoid6test python -m pytest tests/test_notify_integration.py -v -s
```

**Environment Variables:**
- `BBSENGINE6_DBNAME`: Database name to use (default: `bbsengine6`)
- Set to `zoid6test` for testing, `bbsengine6` for production

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

### 9. TestNotificationCount
Test the notification count function:
- `test_count_returns_integer()` - Verify count() returns an integer
- `test_count_for_valid_moniker()` - Count notifications for jam
- `test_count_for_alice()` - Count notifications for alice
- `test_count_for_bob()` - Count notifications for bob

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

## How conftest.py Works

The `py/tests/conftest.py` file provides pytest fixtures for automatic database setup:

### Session-Scoped Fixtures (run once per test session)

**`db_connection`**: Connects to `zoid6test` database as `opencode` user
- Uses oidentd authentication (no password needed)
- Creates database if it doesn't exist
- Connection persists for entire test session

**`schema_init`**: Initializes 7 notify-specific SQL files
- Smart approach: only loads files needed for notify system
- Skips already-existing tables (idempotent)
- Order: notify.sql → notify_recipient.sql → ... → notifyview.sql
- Logs "already exists" warnings on re-runs (this is normal)

**`create_test_users`**: Creates test users
- Inserts `alice` and `bob` into `engine.__member` (skip if exist)
- Uses minimal fields: moniker, email
- `jam` already exists, not re-created

### Function-Scoped Fixtures (run before/after each test)

**`test_transaction`** (autouse):
- Automatically wraps each test in its own transaction
- Schema persists (session fixtures), test data is isolated
- Rolls back after test to keep database clean
- Allows tests to run multiple times without data accumulation

### Helper Functions

**`_get_notify_sql_files()`**: Returns 7 notify SQL files in correct order
**`_read_sql_file()`**: Reads SQL and removes psql metacommands (\set, \echo, etc)
**`_execute_sql_file()`**: Executes SQL, handles "already exists" errors

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
- Ensure PostgreSQL is running: `psql -U opencode -d postgres -c "SELECT 1"`
- Check `zoid6test` database exists: `psql -U opencode -d zoid6test -c "SELECT 1"`
- Check `opencode` user exists in PostgreSQL
- Conftest will create `zoid6test` if it doesn't exist

### "relation does not exist" errors
- Ensure `BBSENGINE6_DBNAME=zoid6test` environment variable is set
- Without it, code connects to wrong database (default: `bbsengine6`)
- Run: `BBSENGINE6_DBNAME=zoid6test pytest tests/test_notify_integration.py`

### "already exists" warnings in conftest logs
- This is **normal and expected** on subsequent test runs
- Tables are persistent, fixtures skip creation
- Warnings can be suppressed (no functional impact)

### Transaction isolation errors
- If tests see "UndefinedTable" errors within a test, it may be a transaction issue
- Check that conftest fixtures ran successfully (look for setup logs)
- Try running tests sequentially: `pytest tests/ -v` (not parallel)

## Next Steps

1. Run unit tests: `pytest tests/test_notify.py -v`
2. Run integration tests: `pytest tests/test_notify_integration.py -v -s`
3. Try manual examples in Python REPL
4. Integrate into your application code
5. Create notifications for real application events
