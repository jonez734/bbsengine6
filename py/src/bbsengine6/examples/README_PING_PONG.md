# Ping/Pong Demo - getch() Idle Loop Notification Detection

**Location:** `bbsengine6/examples/ping_pong_demo.py`  
**Author:** OpenCode  
**Date:** 2026-05-18

**See Also:**
- [GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md) - getch() without daemon model
- [GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md) - multi-member queue isolation

## Overview

This demo showcases a fully interactive **two-player ping/pong message exchange** that demonstrates real-world patterns for using bbsengine6's notification system with the getch() idle loop. Two players (alice and bob) exchange messages concurrently on the same machine, each with their own thread-local member context and isolated notification queue.

### What You'll See

✅ **Real-time message passing** between two concurrent threads  
✅ **getch() idle loop integration** - notifications detected during keyboard input  
✅ **Automatic bell emission** when messages arrive  
✅ **Thread-local member isolation** - alice's queue ≠ bob's queue  
✅ **Comprehensive error handling** for 9+ failure scenarios  
✅ **Interactive keyboard control** with getch_str() for both menu and notifications  
✅ **Visual display** with both menu and persistent message log  
✅ **5-round limit** with ESC key for immediate exit  

## Architecture

### Thread Isolation with Member Context

Each player runs in its own thread with an isolated member context:

```
Alice's Thread                    Bob's Thread
┌──────────────────┐             ┌──────────────────┐
│ _threadlocal.    │             │ _threadlocal.    │
│ moniker="alice"  │             │ moniker="bob"    │
└──────────────────┘             └──────────────────┘
      ↓                                ↓
┌─────────────────┐             ┌─────────────────┐
│ while loop:     │             │ while loop:     │
│ getch(2.0s)     │             │ getch(2.0s)     │
│ ↓ checks queue  │             │ ↓ checks queue  │
│ ↓ emits bell    │             │ ↓ emits bell    │
│ ↓ processes key │             │ ↓ processes key │
└─────────────────┘             └─────────────────┘
      ↓                                ↓
┌──────────────────────────────────────────────────┐
│  Shared Notification System (Thread-Safe)        │
├──────────────────────────────────────────────────┤
│  Queue["alice"] ←── Receives PONG from bob       │
│  Queue["bob"]   ←── Receives PING from alice     │
│  (Protected by _queues_lock, thread-safe)       │
└──────────────────────────────────────────────────┘
```

### Notification Flow

```
Message Exchange Sequence:

Time  Alice Terminal         Bob Terminal            Queue State
────  ──────────────────     ──────────────────      ─────────────
0s    [Start getch loop]     [Start getch loop]      alice: []
      Round 1/5              Round 1/5               bob: []

2s    Waiting...             Waiting...              (timeout, no input)

4s    [User] Presses P       Waiting...              Sends PING to bob
      ✓ Sent PING #1         (checking queue)        alice: []
                                                      bob: [PING#1]

5s    Waiting...             [BELL] 🔔 emits         
                             (getch detects)        

6s    Waiting...             [User] Presses C        Displays PING #1
                             → Shows notification    

7s    Waiting...             [User] Presses P        Sends PONG to alice
                             ✓ Sent PONG #1         alice: [PONG#1]
                                                      bob: []

8s    [BELL] 🔔 emits        Waiting...
      (getch detects)        

9s    [User] Presses F2      Waiting...              Displays PONG #1
      → Shows notification   

10s   [User] Presses P       Waiting...              Sends PING #2
      ✓ Sent PING #2         (continue exchange)     alice: []
      Round 2/5              Round 2/5               bob: [PING#2]

... (repeats for rounds 3, 4, 5)

At Round 6: Either:
A) Both reach round 5 → Demo exits gracefully
B) ESC pressed → Both threads exit immediately
C) Q pressed → That player exits, other continues
D) Error occurs → Handle gracefully, player continues
```

## Key Concepts

### From GETCH_INTEGRATION.md

**The getch() Integration Model** (vs. daemon model):

```
User calls getch() during normal menu navigation
     ↓
getch() checks for pending notifications
     ↓
If notifications found, bell emits and F2 shows them
     ↓
No separate daemon needed
```

This demo shows exactly this pattern. Each player's `getch()` call:
1. Checks for pending notifications in their queue
2. Automatically emits a bell if notifications exist
3. Allows pressing F2 to view them
4. All happens during normal keyboard input

**Benefits for BBS:**
- ✅ Event-driven (check on demand)
- ✅ Minimal resources (no persistent daemon)
- ✅ Fits terminal paradigm
- ✅ Integrated into existing getch() loop
- ✅ Scales to multiple concurrent users

See [GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md) for full details.

### From GETCH_MULTI_USER.md

**Member-Specific Notification Queues:**

```python
# From bbsengine6/io/getch.py
moniker = getattr(_threadlocal, "moniker", None)  # Get CURRENT member

if check_notifications and moniker and _has_notify_module:
    # Count notifications for THIS member only
    has_notifications = notify.count(moniker)
    if has_notifications:
        _emit_notification_bell_once()
```

This demo shows multi-member support:
- **Alice's getch()** checks ONLY alice's queue
- **Bob's getch()** checks ONLY bob's queue
- No cross-member notification leakage
- Built-in thread-local isolation

**Why This Matters:**
- ✅ Multiple concurrent users on same machine
- ✅ Privacy (members only see their notifications)
- ✅ Scalability (no shared state conflicts)
- ✅ Thread-safe (built into Python threading.local)

See [GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md) for full details.

### Thread-Local Member Context

The `_threadlocal` object in bbsengine6/member.py provides thread-isolated storage:

```python
from bbsengine6.member import _threadlocal

# In alice's thread:
_threadlocal.moniker = "alice"
moniker = getattr(_threadlocal, "moniker", None)  # → "alice"

# In bob's thread (simultaneously):
_threadlocal.moniker = "bob"
moniker = getattr(_threadlocal, "moniker", None)  # → "bob"

# No conflicts! Each thread has its own namespace
```

Why this is essential:
- **No parameters needed** - Functions automatically know current user
- **Thread-safe** - Python's threading.local() handles isolation
- **Implicit context** - Just like logged-in username in a BBS session
- **Works everywhere** - Any function can access current moniker

### Notification API Usage

**Registering Types:**
```python
notify.register_type(
    "ping-message",
    rate_limit={"per_user": 100},  # Allow 100 per user
    persist=False                   # Keep in memory only (no database)
)
```

**Sending Messages:**
```python
notify.send(
    notification_type="ping-message",
    recipients=["bob"],             # Route to bob's queue
    template_vars={                 # Message content
        "from": "alice",
        "round": 1,
        "message": "PING #1 from alice",
        "timestamp": "2026-05-18T14:30:00"
    },
    urgency="ROUTINE"
)
```

**Checking Queue:**
```python
# Get queue for current member
queue = notify.get_queue(moniker)

# Retrieve all pending notifications
all_notifs = queue.get_all()

# Count unread
count = notify.count(moniker)
```

**Blocking/Unblocking:**
```python
# Alice blocks Bob's messages
notify.block("alice", "bob")

# Check if blocked
is_blocked = notify.is_blocked("alice", "bob")

# Unblock later
notify.unblock("alice", "bob")
```

## Running the Demo

### Prerequisites

- Python 3.9+
- bbsengine6 installed in your Python environment
- Two terminal windows (for full interactive experience)

### Single Terminal (Same Thread)

For testing purposes, the demo can run in one terminal with both players' loops running sequentially. However, the real power comes from concurrent execution:

```bash
# Run the demo
python -m bbsengine6.examples.ping_pong_demo

# Follow the interactive prompts
```

### Two Terminals (Concurrent, Recommended)

For the most realistic demonstration:

**Terminal 1 (Alice):**
```bash
python -m bbsengine6.examples.ping_pong_demo
```

**Terminal 2 (Bob):**
```bash
python -m bbsengine6.examples.ping_pong_demo
```

Both will connect to the same shared notification system and can exchange messages in real-time.

### User Controls

| Key | Action |
|-----|--------|
| `P` or `p` | Send ping/pong to other player |
| `C` or `c` | Check/display all pending notifications |
| `F2` | Show pending notifications (getch() native) |
| `ESC` | Quit immediately (both players exit) |
| `Q` or `q` | Quit local player (other continues) |
| (timeout) | getch() automatically checks queue every 2 seconds |

### Example Session

```
Terminal 1: Alice's Game
═════════════════════════════════════════════════
    PING-PONG DEMO (Moniker: ALICE)
═════════════════════════════════════════════════
Round: 1/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────
MESSAGE LOG:
  [Awaiting first message...]
─────────────────────────────────────────────────
Queue Status: 0 pending notification(s)
═════════════════════════════════════════════════
[User types: p]
✓ Sent PING #1 to bob


Terminal 2: Bob's Game
═════════════════════════════════════════════════
    PING-PONG DEMO (Moniker: BOB)
═════════════════════════════════════════════════
Round: 1/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────
MESSAGE LOG:
  [Awaiting first message...]
─────────────────────────────────────────────────
Queue Status: 0 pending notification(s)
═════════════════════════════════════════════════
[2 seconds pass, getch() timeout]
[BELL] 🔔 
Queue Status: 1 pending notification(s)

[User types: c]
─── Pending Notifications for bob ───
[ROUTINE ] 2026-05-18T14:30:00 | PING #1 from alice
──────────────────────────────────────────

MESSAGE LOG:
  [14:30:01] PING #1 from alice
```

## Error Handling Demonstration

The demo includes comprehensive error handling for common failure scenarios. These are automatically demonstrated or can be triggered manually:

### Scenario A: Sending to Offline Player

**What happens:**
```
[User presses P]
❌ ERROR: bob is not logged in
   (Is bob logged in? Check other terminal)
```

**How to trigger:**
1. Start only alice's terminal
2. Press P to send to bob
3. See the error message

### Scenario B: Rate Limiting

**What happens:**
```
[User presses P multiple times rapidly]
❌ ERROR: Failed to send: rate limit exceeded
   → You've sent too many messages too quickly
   → Please wait a moment before sending again
```

**How to trigger:**
1. Both players running
2. One player rapidly presses P (20+ times)
3. System enforces rate limit

### Scenario C: Blocked Messages

**What happens:**
```
notify.block("alice", "bob")
[Bob tries to send]
❌ ERROR: Failed to send: message blocked
   → alice has blocked your messages
```

**How to trigger:**
1. Both players running
2. Add to demo code: `notify.block("alice", "bob")`
3. Try to send from bob
4. See block error

### Scenario D: Queue Access Errors

**What happens:**
```
❌ Queue not found for alice
```

**How to trigger:**
1. Press C before full initialization
2. Or if queue cleanup happens mid-game

### Scenario E: Early Exit (One Player Quits)

**What happens:**
```
Terminal 1: [User presses Q]
✓ Alice: Quit
✓ Alice's game ended

Terminal 2: [Continues to Round 5]
[Can still send, but messages go nowhere]
✓ Bob: Completed 5 rounds!
✓ Bob's game ended
```

**How to trigger:**
1. Both players running
2. One player presses Q
3. Other player continues

### Scenario F: Immediate Exit (ESC Key)

**What happens:**
```
Terminal 1: [User presses ESC]
✓ ESC pressed - exiting demo
✓ Alice's game ended

Terminal 2: [Immediately exits]
✓ ESC pressed - exiting demo
✓ Bob's game ended
```

**How to trigger:**
1. Both players running
2. Either player presses ESC
3. Both threads exit gracefully

### Scenario G: Empty Queue Check

**What happens:**
```
[User presses C]
✓ No pending notifications for alice
```

**How to trigger:**
1. Both players running
2. Press C before any messages arrive
3. See the "no messages" response

### Scenario H: Malformed Notification (Edge Case)

**What happens:**
```
⚠ Malformed notification: 'NoneType' object has no attribute 'message'
```

**How to trigger:**
1. Rarely happens in normal operation
2. Protected by try/catch in display functions

### Scenario I: Thread Synchronization

**What happens:**
```
❌ Partner disconnected. Exiting...
```

**How to trigger:**
1. Check happens if active thread count drops below expected
2. Gracefully exits if partner dies unexpectedly

## Expected Output

### Successful Run (5 Complete Rounds)

```
╔════════════════════════════════════════════════════════════╗
║  BBSENGINE6 PING-PONG DEMO                                 ║
║  Demonstrates getch() idle loop notification detection      ║
║  with multi-member per-machine support                      ║
╚════════════════════════════════════════════════════════════╝

This demo shows:
  • Two concurrent players (alice and bob) on same machine
  • Thread-local moniker isolation for per-member queues
  • getch() integration for automatic notification detection
  • Bell emission when notifications arrive
  • Comprehensive error handling for failure scenarios

For full documentation, see: README_PING_PONG.md

Press Enter to start...
✓ Notification types registered

Starting two concurrent player threads...
✓ alice initialized (moniker=alice)
✓ bob initialized (moniker=bob)

[Player exchanges 5 complete rounds...]

✓ alice: Completed 5 rounds!
✓ alice's game ended
✓ bob: Completed 5 rounds!
✓ bob's game ended

╔════════════════════════════════════════════════════════════╗
║  Demo Complete!                                            ║
║                                                            ║
║  You've seen:                                              ║
║    ✓ getch() notification checking                         ║
║    ✓ Thread-local member isolation                         ║
║    ✓ Per-member notification queues                        ║
║    ✓ Multi-user concurrent messaging                       ║
║    ✓ Error handling for edge cases                         ║
║                                                            ║
║  See README_PING_PONG.md for more information              ║
╚════════════════════════════════════════════════════════════╝
```

## What You'll Learn

### Practical Knowledge

1. **How to use bbsengine6.notify API:**
   - `register_type()` - Set up notification categories
   - `send()` - Send messages to recipients
   - `get_queue()` - Access in-memory message queue
   - `block()`/`unblock()` - Control message blocking

2. **How to use bbsengine6.io.getch() with notifications:**
   - `getch_str(timeout=X)` - Get keystroke with timeout
   - Automatic notification checking during keypresses
   - Bell emission when messages arrive
   - F2 key for displaying notifications

3. **Thread-local member context:**
   - `_threadlocal.moniker` - Per-thread member identity
   - Why it's essential for multi-user systems
   - How Python's threading.local() provides isolation

4. **Multi-user message patterns:**
   - Concurrent threads with separate contexts
   - Thread-safe queue operations
   - Error handling for concurrent operations
   - Graceful degradation when users disconnect

### Architecture Patterns

1. **Member Context Pattern:**
   ```python
   _threadlocal.moniker = "alice"
   # Now all functions know current user without parameters
   ```

2. **Notification Type Registration:**
   ```python
   notify.register_type("message-type", rate_limit={...}, persist=False)
   ```

3. **Event Firing with Member Context:**
   ```python
   notify.send(notification_type="...", recipients=["bob"], ...)
   ```

4. **getch() with Notification Checking:**
   ```python
   key = getch.getch_str(timeout=2.0)  # Auto-checks queue
   ```

5. **Error Handling Pattern:**
   ```python
   try:
       queue = notify.get_queue(moniker)
       if queue is None:
           # Handle not logged in
       messages = queue.get_all()
   except Exception as e:
       # Handle errors gracefully
   ```

## Code Organization

The demo script is structured as:

```python
# Setup
setup_notifications()           # Register notification types

# Player Threads
def player_loop(moniker):      # Main game loop
    display_menu()             # Show UI
    key = getch.getch_str()    # Get input (auto-checks queue)
    process_input(key)         # Handle P/C/Q/ESC

# Supporting Functions
send_ping()                    # Send message with error handling
check_and_display_queue()      # Show pending notifications
clear_screen()                 # UI helper

# Main
main()                         # Entry point, thread orchestration
```

## Integration with Existing Docs

This demo is designed as a practical companion to:

1. **[GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md)**
   - Demonstrates the "getch() Integration Model (Recommended for BBS)"
   - Shows no-daemon pattern in action
   - Proves event-driven notifications work

2. **[GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md)**
   - Demonstrates "Multi-Member Per Machine Support"
   - Shows thread-local moniker isolation
   - Proves member-specific queues work correctly

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'bbsengine6'"

**Solution:**
```bash
# Ensure bbsengine6 is installed
cd /path/to/bbsengine6/py
pip install -e .
```

### Issue: "Cannot connect to other player's queue"

**Solution:**
- Ensure both terminals are running with the demo
- Check that both threads are initialized (wait for "initialized" messages)

### Issue: Bell doesn't emit

**Solution:**
- Terminal may have bell disabled
- Check terminal bell settings
- Demo will still show queue status even without audible bell

### Issue: getch() timeout seems long

**Solution:**
- Timeout is set to 2.0 seconds for stability
- Can be adjusted in `ping_pong_demo.py` by changing `GETCH_TIMEOUT`

### Issue: One terminal freezes

**Solution:**
- Press ESC in the other terminal to force exit
- Or Ctrl+C in the frozen terminal
- Demo has timeout protection but ESC is fastest

## References

- **bbsengine6 notify API:** See `bbsengine6/notify.py`
- **getch() implementation:** See `bbsengine6/io/getch.py`
- **Member context:** See `bbsengine6/member.py`
- **Getch Integration Guide:** [GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md)
- **Multi-User Guide:** [GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md)

## Summary

This demo transforms abstract documentation into concrete, working code. You can see exactly how:

✅ getch() idle loop detects notifications automatically  
✅ Thread-local member context provides isolation  
✅ Per-member notification queues prevent cross-talk  
✅ Multi-user concurrent messaging works in practice  
✅ Error handling maintains stability  

Run it, explore the code, and use these patterns in your own bbsengine6 applications!
