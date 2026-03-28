# Notifications During Input - How It Works

## The Challenge

When a user is waiting for input (blocked in `inputstring()` or `inputchoice()`), the main thread cannot run any background code. However, we still want notifications to be delivered and queued for later processing.

## The Solution: Asynchronous Queue Pattern

The notification system uses **threading** to handle this:

```
┌─────────────────────────────────────────────────────────────────┐
│                     NOTIFICATION SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Main Thread (Blocked)          Background Thread               │
│  ┌──────────────────┐            ┌──────────────────┐          │
│  │  inputstring()   │◄──────────┤  notify.send()   │          │
│  │  blocking        │            │  (non-blocking)  │          │
│  │  waiting for     │            │  adds to queue   │          │
│  │  user input      │            │  returns         │          │
│  └──────────────────┘            └──────────────────┘          │
│           │                              ↑                      │
│           │                              │                      │
│           └──────────────────────────────┘                      │
│                     Queue (accumulates notifications)           │
│                     - Non-blocking                              │
│                     - Thread-safe                               │
│                     - Can grow while main blocked               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Key Points

### 1. Non-Blocking Design
- **Database writes** are fast (microseconds)
- **Queue operations** are instant (O(1))
- No locks or waits
- Sender doesn't block

### 2. Thread-Safe Queue
- Uses Python's `queue.Queue` internally
- Atomic operations (thread-safe by design)
- Main thread can check size anytime
- Multiple producers, single consumer

### 3. Two Persistence Layers

**Live Queue** (`get_queue()`)
- In-memory accumulation
- Lost on application restart
- Sub-millisecond access
- Perfect for notifications during session

**Database** (`get_notifications()`)
- Permanent storage
- Survives restarts
- Used as fallback when app starts
- Used for historical queries

## The Pattern

### Before Opening Input

```python
# Load any unread notifications from last session
unread = get_notifications("jam", unread_only=True, limit=10)
if unread:
    for notif in unread:
        display_notification(notif)
        mark_read(notif.id, "jam")
```

### During Input (User Blocked)

```python
# Get queue reference before user input
queue = get_queue("jam")

# User now blocked in input - main thread waiting
name = inputstring("Enter your name: ")

# Background notifications are quietly accumulating in queue
# No exceptions, no blocking, no interruptions
```

### After Input Completes

```python
# Main thread unblocked, check what arrived
while queue.size() > 0:
    notifications = queue.get_all()
    for notif in notifications:
        display_notification(notif)
        mark_read(notif.id, "jam")
```

## Practical Example

```python
from bbsengine6.notify import get_queue, get_notifications, mark_read
from bbsengine6.io import inputstring, echo

def get_user_input_with_notifications(prompt):
    """Get user input while handling accumulated notifications."""
    
    # Step 1: Show any unread from database
    echo("\n--- Checking for unread notifications ---\n")
    unread = get_notifications("jam", unread_only=True, limit=5)
    for notif in unread:
        echo(f"[{notif.urgency.value}] {notif.message}")
        mark_read(notif.id, "jam")
    
    # Step 2: Prepare queue
    queue = get_queue("jam")
    
    # Step 3: User blocked in input
    echo(f"\n--- Waiting for input ---\n")
    user_input = inputstring(prompt)
    
    # Step 4: Process queue that accumulated
    echo(f"\n--- Processing notifications that arrived ---\n")
    while queue.size() > 0:
        notif = queue.get_all()[0]
        echo(f"[{notif.urgency.value}] {notif.message}")
        mark_read(notif.id, "jam")
    
    return user_input

# Usage
name = get_user_input_with_notifications("Enter your name: ")
```

## What Happens Behind the Scenes

### When `notify.send()` is Called (Background)

```
1. Validate input
2. Register type if needed
3. Check rate limits
4. Insert into database (fast!)
5. For each recipient:
   a. Insert delivery record
   b. Check if user has queue
   c. If yes: add to queue (O(1))
   d. If no: notification in DB, available next session
6. Return success
```

### When Main Thread Checks Queue

```
queue.size()        # Returns number of queued notifications (O(1))
queue.get_all()     # Atomically empties queue (O(n))
queue.has_urgent()  # Checks for URGENT/CRITICAL (O(n))
```

## Handling Different Scenarios

### Scenario 1: Notification Arrives While User Typing
```
Time 0s:  inputstring("Enter name: ") called
Time 2s:  notify.send() called (background thread)
          → Added to queue silently
          → Main thread still waiting for input
Time 5s:  User enters "alice" and presses Enter
Time 5s:  queue.size() returns 1
          → Display notification
          → Continue
```

### Scenario 2: Multiple Notifications While User In Menu
```
Time 0s:  inputchoice(["Option 1", "Option 2"]) called
Time 1s:  notify.send() - notification 1 added to queue
Time 2s:  notify.send() - notification 2 added to queue
Time 3s:  notify.send() - notification 3 added to queue
Time 4s:  User selects option 1, input returns
Time 4s:  queue.size() returns 3
          → Process all 3 notifications
```

### Scenario 3: Urgent Notification Interrupt
```
Time 0s:  inputstring("Enter command: ") called
Time 2s:  notify.send(urgency=CRITICAL)
          → Added to queue
Time 2s:  Application can check queue.has_urgent()
          → If true, could interrupt input (application decision)
          → Or just queue and process after
```

## Important Properties

### Thread Safety ✓
- `queue.Queue` is thread-safe by design
- No locks needed by caller
- Safe for concurrent access

### Non-Blocking ✓
- `send()` returns immediately
- No waiting or retries
- Exceptions only for validation, not I/O

### Persistent ✓
- Database backup if app crashes
- Can load unread notifications on restart
- Queue is ephemeral (lost on restart)

### Ordered ✓
- Database queue preserved chronologically
- Live queue FIFO order
- Can combine both for full history

## Code Example: Full Workflow

```python
from bbsengine6.notify import (
    send, get_queue, get_notifications, mark_read, 
    register_type, NotificationUrgency
)
from bbsengine6.io import inputstring, echo

# Initialize
register_type("DEMO", NotificationUrgency.IMPORTANT, max_per_hour=100)

# Before input: load from database
echo("Unread notifications:")
for notif in get_notifications("jam", unread_only=True):
    echo(f"  - {notif.message}")
    mark_read(notif.id, "jam")

# Get queue reference
queue = get_queue("jam")

# User input (background notifications accumulate here)
name = inputstring("What's your name? ")

# After input: process queue
echo(f"\nHello {name}! You have {queue.size()} new notifications:")
for notif in queue.get_all():
    echo(f"  - {notif.message}")
    mark_read(notif.id, "jam")
```

## Testing

The demo script `example_notify_with_input.py` shows this in action with threading:

```bash
cd /home/opencode/data/work/bbsengine6
python example_notify_with_input.py
```

This simulates:
- Main thread blocked in input
- Background threads sending notifications
- Queue accumulating in real-time
- Main thread processing after

## Summary

The notification system is designed to work seamlessly with blocking input operations:

✓ Notifications don't block user input
✓ Multiple notifications accumulate
✓ System remains responsive
✓ Fallback to database if app restarts
✓ Simple queue pattern for application code

The key is checking the queue **after** input returns, not during.
