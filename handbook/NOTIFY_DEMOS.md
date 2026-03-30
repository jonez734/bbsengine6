# Notification System Demo Scripts

This directory contains demo scripts showing the notification system in action, including **notifications arriving while users are in input dialogs**.

## Available Demos

### 1. `example_notify.py` - Basic Examples
**7 practical examples of notification features**

```bash
cd /home/opencode/data/work/bbsengine6
python example_notify.py
```

**Examples:**
- Basic notification sending
- Different urgency levels (ROUTINE, IMPORTANT, URGENT, CRITICAL)
- Notifications with structured data
- Group-based targeting
- User blocking
- Retrieving notifications from database
- Complete send→receive→read workflow

**Output:** Shows messages like:
```
Hello Jam, welcome to bbsengine6!
[ROUTINE  ] Regular update
[IMPORTANT] Important announcement
[URGENT   ] Urgent action needed
```

### 2. `example_notify_with_input.py` - Input Integration
**Demonstrates notifications working while user interacts with input dialogs**

```bash
cd /home/opencode/data/work/bbsengine6
python example_notify_with_input.py
```

**Scenarios:**
1. **Notifications during inputstring()** - User typing while notifications arrive
2. **Notifications during inputchoice()** - User selecting menu while notifications arrive
3. **Queue accumulation** - Multiple notifications arriving in background
4. **Urgent notification interrupt** - URGENT notification during routine work
5. **Practical pattern** - Recommended code pattern for handling queue

**Key Feature:** Uses threading to simulate background notifications while main thread is blocked in input dialogs

**Output example:**
```
Simulating user input now...

Imagine user is here: inputstring('Enter your name: ')

While waiting for input, notifications arrive in background...

  [Main] Second 1... user still typing...
  [Main] Second 2... user still typing...

[BACKGROUND THREAD] Sending first notification...
  [Main] Second 3... user still typing...

⚠️  1 notification(s) in queue!
```

## How It Works: Notifications During Input

### The Problem
When user is blocked in `inputstring()` or `inputchoice()`, the main thread can't receive new notifications. The solution is **asynchronous queuing**:

```
Main Thread (Blocked)          Background Thread
┌─────────────────┐          ┌──────────────────┐
│ inputstring()   │          │ receive_notify() │
│ blocking...     │          │ add to queue     │
│                 │◄────────┤ return           │
│ (can't run code)│          │                  │
└─────────────────┘          └──────────────────┘
                             ↓
                        Queue (accumulates)
                             ↓
                        Main Thread checks
                        after input returns
```

### The Solution
Use the notification **queue** to accumulate notifications:

```python
# Get queue for user
queue = get_queue("jam")

# User in input (main thread blocked)
name = inputstring("Enter name: ")

# After input, check queue (notifications arrived while typing)
while queue.size() > 0:
    notif = queue.get_all()[0]
    display_notification(notif.message)
    mark_read(notif.id, "jam")
```

## Pattern: Recommended Code

```python
from bbsengine6.notify import (
    get_notifications,
    get_queue,
    mark_read
)
from bbsengine6.io import inputstring

# Step 1: Load unread from database BEFORE input
unread = get_notifications("jam", unread_only=True, limit=10)
if unread:
    for notif in unread:
        echo(f"Unread: {notif.message}")

# Step 2: User in input (queue accumulates in background)
queue = get_queue("jam")
name = inputstring("Enter your name: ")

# Step 3: Process queue AFTER input completes
while queue.size() > 0:
    notifications = queue.get_all()
    for notif in notifications:
        echo(f"New: {notif.message}")
        mark_read(notif.id, "jam")
```

## Running the Tests

### Unit Tests (No DB Required)
```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest tests/test_notify.py -v
```
**Result:** 37 tests pass
- Validation functions
- Data structures
- Queue operations
- Template rendering

### Integration Tests (Requires DB)
```bash
cd /home/opencode/data/work/bbsengine6/py
python -m pytest tests/test_notify_integration.py -v -s
```
**Result:** 8 test classes, multiple examples each
- Sending and receiving
- Groups
- Blocking
- Retrieval
- Queuing
- Type management
- Rate limiting
- Complete workflows

## Key Concepts

### 1. Live Queue vs Database
- **Live Queue** (`get_queue()`) - In-memory queue for active sessions
  - Accumulates notifications while user is busy
  - Lost when application restarts
  - Low latency

- **Database** (`get_notifications()`) - Persistent storage
  - Survives restarts
  - Can query historical notifications
  - Slower but permanent

### 2. Urgency Levels
```python
NotificationUrgency.ROUTINE    # Show in list, no interruption
NotificationUrgency.IMPORTANT  # May highlight or show indicator
NotificationUrgency.URGENT     # Show immediately to active users
NotificationUrgency.CRITICAL   # Interrupt input, show popup
```

### 3. Recipient Types
```python
# Direct user
notify.send(recipients=["jam"], ...)

# Group
notify.send(recipients=["@guild:dragons"], ...)

# Magic @everyone (expands to active sessions)
notify.send(recipients=["@everyone"], ...)

# Mix
notify.send(recipients=["jam", "alice", "@guild:dragons"], ...)
```

### 4. Queue Methods
```python
queue = get_queue("jam")

queue.size()           # How many notifications queued
queue.has_urgent()     # Any URGENT or CRITICAL?
queue.get(timeout=5)   # Block until notification (5s timeout)
queue.get_all()        # Get all without blocking
queue.peek_urgent()    # Check urgent without removing
```

## Real-World Integration

### Game Victory Notification
```python
def on_victory(player, opponent, reward):
    notify.send(
        notification_type="GAME_VICTORY",
        recipients=[player],
        template="You defeated {opp}! Earned {reward} credits.",
        template_vars={"opp": opponent, "reward": reward},
        urgency=NotificationUrgency.URGENT,
        data={"opponent_id": opponent, "reward": reward}
    )
```

### Social Feature Notification
```python
def on_post_shared(sharer, recipient, post_id, title):
    notify.send(
        notification_type="POST_SHARED",
        recipients=[recipient],
        sender_moniker=sharer,
        template="{sender} shared: {title}",
        template_vars={"sender": sharer, "title": title},
        urgency=NotificationUrgency.IMPORTANT,
        data={"post_id": post_id, "shared_by": sharer}
    )
```

### Group Announcement
```python
def announce_to_guild(guild_name, message):
    notify.send(
        notification_type="GUILD_ANNOUNCEMENT",
        recipients=[f"@guild:{guild_name}"],
        template="Guild announcement: {msg}",
        template_vars={"msg": message},
        urgency=NotificationUrgency.IMPORTANT
    )
```

## Troubleshooting

### "Queue is empty but user should have notifications"
Check that:
1. User exists in database (`engine.__member`)
2. `get_queue(user)` called before notifications sent
3. Notifications are configured with `should_persist=True` for database fallback

### "Notifications lost when app restarts"
This is expected for live queue. Solution:
1. Load unread from database on startup
2. Use queue for new notifications during session

### "Rate limit exceeded"
Type has hit its hourly limit. Options:
1. Wait for window to expire (1 hour)
2. Increase limit with `set_rate_limit(type_name, new_limit)`
3. Use different notification type

## Performance Notes

- **Queue operations:** O(1) - constant time
- **Send:** O(n) where n = recipients
- **Rate limit check:** O(1) with index
- **Blocking check:** O(1) with index
- **Group expansion:** O(m) where m = group size

## Next Steps

1. Run `example_notify.py` - basic functionality
2. Run `example_notify_with_input.py` - input integration
3. Run pytest tests - comprehensive testing
4. Integrate into application code
5. Create notifications for real application events

