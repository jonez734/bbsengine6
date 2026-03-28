# bbsengine6 Notification System

## Quick Start

1. **Understand the system**: Read `NOTIFY_INPUT_INTEGRATION.md` (8.8 KB)
2. **See it in action**: Run `python example_notify_with_input.py`
3. **Run the tests**: `pytest py/tests/test_notify.py -v`
4. **Integrate**: Use patterns from `example_notify.py` and `NOTIFY_DEMOS.md`

## The Key Feature

**Notifications work while users are in `inputstring()` or `inputchoice()`**

When a user is blocked waiting for input, notifications arrive in the background and accumulate in a thread-safe queue. When the user finishes input, your application processes the queue.

## Files Overview

### Documentation (READ THESE FIRST)

| File | Size | Purpose |
|------|------|---------|
| `NOTIFY_INPUT_INTEGRATION.md` | 8.8 KB | **START HERE** - How notifications work during input |
| `NOTIFY_DEMOS.md` | 8.1 KB | Demo guide, patterns, and examples |
| `NOTIFY_TESTING.md` | 6.2 KB | Testing guide and SQL queries |
| `handbook/specs/notify.spec` | 638 lines | Complete technical specification |

### Demo Scripts

| File | Size | Purpose |
|------|------|---------|
| `example_notify_with_input.py` | 12 KB | **KEY DEMO** - Notifications during input with threading |
| `example_notify.py` | 8.5 KB | 7 basic examples of all features |

### Implementation Files

| File | Size | Lines | Purpose |
|------|------|-------|---------|
| `py/src/bbsengine6/notify.py` | - | 959 | Main notification module (17 functions) |
| `py/tests/test_notify.py` | - | - | 37 unit tests (all passing) |
| `py/tests/test_notify_integration.py` | - | - | 8 test classes with examples |

### SQL Schema (7 Files)

```
py/src/bbsengine6/sql/
├── notify.sql              # Core notifications table
├── notify_recipient.sql    # Per-user delivery/read tracking
├── notify_block.sql        # One-way blocking relationships
├── notify_group.sql        # Group memberships
├── notify_type.sql         # Type registration & rate limits
├── notify_rate_limit.sql   # Rate limit tracking
└── notifyview.sql          # 4 public views
```

## The Pattern

This is the most important code pattern to understand:

```python
from bbsengine6.notify import get_queue, get_notifications, mark_read
from bbsengine6.io import inputstring

# Step 1: Load unread from database BEFORE input
unread = get_notifications("jam", unread_only=True)
for notif in unread:
    display(notif.message)
    mark_read(notif.id, "jam")

# Step 2: Prepare queue (notifications will accumulate here)
queue = get_queue("jam")

# Step 3: User in input (main thread blocked)
#         Background notifications quietly accumulate
name = inputstring("Enter your name: ")

# Step 4: Process queue that accumulated
while queue.size() > 0:
    notif = queue.get_all()[0]
    display(notif.message)
    mark_read(notif.id, "jam")
```

**Key Point**: Check the queue **after** input returns, not during.

## How It Works (Threading)

```
Main Thread                Background
┌─────────────────────┐   ┌──────────────────┐
│ inputstring()       │   │ notify.send()    │
│ (blocked)           │←──┤ (non-blocking)   │
│ waiting for input   │   │ adds to queue    │
└─────────────────────┘   └──────────────────┘
        ↓
   Queue accumulates
   (thread-safe)
        ↓
   Input returns
        ↓
   Main thread checks
   queue.size()
        ↓
   Processes accumulated
   notifications
```

## Running Tests

```bash
# Unit tests (no database required)
cd py
python -m pytest tests/test_notify.py -v
# Result: 37 tests pass

# Integration tests with examples
cd py
python -m pytest tests/test_notify_integration.py -v -s

# Demo with threading simulation
cd ..
python example_notify_with_input.py

# Basic examples
python example_notify.py
```

## 17 Public Functions

### Sending
- `send()` - Unified notification dispatch with templating

### Receiving
- `get_notifications()` - Retrieve from database
- `get_queue()` - Get live queue for user
- `get_urgent()` - Get high-priority notifications

### Marking
- `mark_read()` - Mark as read
- `mark_delivered()` - Mark as delivered

### Type Management
- `register_type()` - Register notification type
- `get_types()` - List all types
- `set_rate_limit()` - Change rate limits

### Groups
- `create_group()` - Create group
- `add_to_group()` - Add member
- `remove_from_group()` - Remove member
- `get_group_members()` - List members

### Blocking (One-Way)
- `block()` - Block sender
- `unblock()` - Unblock sender
- `is_blocked()` - Check if blocked
- `get_blocked()` - List blockers

## Features

✨ **Safe Template System**
- `{variable}` syntax only
- No code execution or expressions
- Full validation

✨ **Urgency Levels**
- ROUTINE: Show in list, no interruption
- IMPORTANT: Highlight or show indicator
- URGENT: Show immediately
- CRITICAL: Interrupt input

✨ **Recipient Types**
- Direct: `["jam", "alice"]`
- Groups: `["@guild:dragons"]`
- Magic @everyone: `["@everyone"]`
- Mix: `["jam", "@guild:dragons"]`

✨ **Thread-Safe Operations**
- Queue uses Python's `queue.Queue`
- O(1) operations for accumulation
- Non-blocking send

✨ **Dual Persistence**
- Live queue (in-memory, lost on restart)
- Database (permanent, queryable)

## Real-World Examples

See `example_notify.py` for:
- Game victory notifications
- Social feature notifications (post sharing)
- Guild announcements
- Complete workflows

## Production Ready

✓ All code formatted with `ruff`
✓ All tests passing (37 unit tests)
✓ Comprehensive input validation
✓ Proper error handling
✓ Thread-safe design
✓ Git committed (35cbd51)

## Troubleshooting

**"Notifications lost when app restarts"**
- Expected: Live queue is ephemeral
- Solution: Load unread from database on startup

**"Queue is empty but notifications should exist"**
- Check: User exists in `engine.__member`
- Check: `get_queue()` called before `notify.send()`

**"Rate limit exceeded"**
- Type hit hourly limit
- Solution: Wait 1 hour or increase limit with `set_rate_limit()`

## Next Steps

1. Read `NOTIFY_INPUT_INTEGRATION.md` (10 min read)
2. Run `example_notify_with_input.py` (see it work)
3. Run pytest (verify everything passes)
4. Look at patterns in `example_notify.py`
5. Integrate `notify.send()` into your application code

## Contact

For questions about the notification system, see:
- `NOTIFY_INPUT_INTEGRATION.md` - Threading and how it works
- `NOTIFY_DEMOS.md` - Practical patterns
- `handbook/specs/notify.spec` - Complete technical details
