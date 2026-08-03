# Ping/Pong Demo - Implementation Plan

> **STATUS (2026-07-22): SUPERSEDED.** This plan
> depends on `bbsengine6/notifyd/GETCH_INTEGRATION.md`
> and `bbsengine6/notifyd/GETCH_MULTI_USER.md`, neither
> of which exists. The notifyd daemon was never built,
> and the `bbsengine6.notify` package that this demo
> would use was deleted in Phase 7 of
> `TODO-message-migration.md` (2026-07-22).
>
> A live ping/pong demo is straightforward to implement
> against the current `py/src/bbsengine6/message.py`
> channel pub/sub system (see
> `py/src/bbsengine6/net/SPEC.md` "BED Daemon" for the
> transport) but should be re-scoped from scratch — the
> "two concurrent threads" model in this plan maps to
> "two `BED` processes talking over a shared
> `ChannelState`" in the live system, not to per-member
> notification queues.
>
> The actual daemon to use as a reference is
> `py/src/bbsengine6/bed.py`; the closest live message
> client is in `py/src/bbsengine6/startup/message_subscription.py`.

**Status:** Ready for implementation (and superseded)
**Date Created:** 2026-05-18  
**Original references (DO NOT FOLLOW):** 
- ~~[GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md)~~ — file does not exist (never built)
- ~~[GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md)~~ — file does not exist (never built)

## Overview

A comprehensive two-node ping/pong message exchange demo that showcases:

✅ Real-time message passing between two concurrent threads using bbsengine6 notification API  
✅ getch() idle loop integration for automatic notification detection  
✅ Thread-local moniker isolation for per-member notification queues  
✅ Full interactive control with keyboard input via getch_str()  
✅ Comprehensive error handling for failure scenarios (8+ cases)  
✅ Visual display with both menu and message log  
✅ 5-round maximum with ESC key to quit  

## Architecture

### Thread Isolation with getch() Loop

```
Alice's Thread                    Bob's Thread
┌──────────────────┐             ┌──────────────────┐
│ _threadlocal.    │             │ _threadlocal.    │
│ moniker="alice"  │             │ moniker="bob"    │
└──────────────────┘             └──────────────────┘
      ↓                                ↓
┌─────────────────┐             ┌─────────────────┐
│ while loop:     │             │ while loop:     │
│ getch(timeout)  │             │ getch(timeout)  │
│ ↓ checks queue  │             │ ↓ checks queue  │
│ ↓ emits bell    │             │ ↓ emits bell    │
│ ↓ processes key │             │ ↓ processes key │
└─────────────────┘             └─────────────────┘
      ↓                                ↓
┌──────────────────────────────────────────────────┐
│  Shared Notification System                      │
├──────────────────────────────────────────────────┤
│  Queue["alice"] ←── Receives PONG from bob       │
│  Queue["bob"]   ←── Receives PING from alice     │
│  (Thread-safe access via _queues_lock)          │
└──────────────────────────────────────────────────┘
```

### Notification Flow

```
FULL DEMO SEQUENCE WITH ERROR SCENARIOS
═══════════════════════════════════════

Time  Alice                     Bob                     Queue State
────  ─────                     ───                     ─────────────
0s    Start getch loop          Start getch loop        alice: [], bob: []
      Round 1/5                 Round 1/5

2s    Timeout, no input         Timeout, no input       (no change)

4s    [User] Presses "P"        Waiting...              Sends PING
      → notify.send(bob)                                alice: [], bob: [PING#1]
      ✓ Sent PING #1

5s    Waiting...                getch() timeout         
                                → bell emits! 🔔
                                (automatic)

6s    Waiting...                [User] Presses "C"      
                                → Displays PING #1      
                                Message log updated

7s    Waiting...                [User] Presses "P"      
                                → notify.send(alice)   bob sends PONG
                                ✓ Sent PONG #1         alice: [PONG#1], bob: []

8s    getch() timeout           Waiting...              
      → bell emits! 🔔                                  
      (automatic)

9s    [User] Presses "F2"       Waiting...
      → Displays PONG #1
      Message log updated

10s   [User] Presses "P"        Waiting...              alice: [], bob: []
      → notify.send(bob)        (continue ping/pong)    Sends PING #2
      Round 2/5

... (repeats for rounds 3, 4, 5)

At Round 6: One of these happens:
A) Both reach 5 rounds → Demo exits gracefully
B) [User] Presses ESC → Both threads exit immediately
C) [User] Presses "Q" → That thread exits, other continues until round 5
D) Error occurs (recipient offline, rate limit, etc.) → Handle gracefully
```

## User Interface

### Terminal Layout for Each Player

```
═══════════════════════════════════════════════════════
    ALICE'S PING-PONG DEMO (Moniker: alice)
═══════════════════════════════════════════════════════
Round: 2/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────────
MESSAGE LOG:
  [2024-05-18 14:30:01 ROUTINE] PONG #1 from bob
  [2024-05-18 14:30:05 ROUTINE] PONG #2 from bob
  [2024-05-18 14:30:09] ✓ Sent PING #3
  [Awaiting next message...]

─────────────────────────────────────────────────────
Queue Status:
  Pending in alice's queue: 2 unread
  Last check: 2024-05-18 14:30:05

═══════════════════════════════════════════════════════
```

## User Controls

| Key | Action |
|-----|--------|
| `P` or `p` | Send ping/pong to other player |
| `C` or `c` | Check/display pending notifications |
| `F2` | Show pending notifications (getch() native feature) |
| `ESC` | Quit immediately (both players exit) |
| `Q` or `q` | Quit local player (other continues) |
| (timeout) | getch() automatically checks queue and emits bell |

## API Usage

### Core bbsengine6 APIs Used

**Notification Registration:**
```python
notify.register_type(
    "ping-message",
    rate_limit={"per_user": 100},
    persist=False
)
```

**Notification Sending:**
```python
notify.send(
    notification_type="ping-message",
    recipients=["bob"],
    template_vars={...},
    urgency="ROUTINE"
)
```

**Notification Retrieval:**
```python
queue = notify.get_queue("alice")
all_notifs = queue.get_all()
count = notify.count("alice")
```

**Member Context (Thread-Local):**
```python
from bbsengine6.member import _threadlocal
_threadlocal.moniker = "alice"  # Set during "login"
current_moniker = getattr(_threadlocal, "moniker", None)
```

**Keyboard Input with Notification Checking:**
```python
from bbsengine6.io import getch
key = getch.getch_str(timeout=2.0)  # Checks notifications automatically
```

**Blocking/Unblocking:**
```python
notify.block("alice", "bob")
is_blocked = notify.is_blocked("alice", "bob")
notify.unblock("alice", "bob")
```

## Error Handling Scenarios

### Scenario A: Sending to Non-Existent User
```
User presses P but recipient hasn't logged in
→ notify.send() fails (recipient queue doesn't exist)
→ Display: "❌ ERROR: Failed to send to [user]"
→ Suggest checking other terminal
```

### Scenario B: Notification Type Not Registered
```
Attempted send before setup_notifications() called
→ notify.send() raises KeyError
→ Display: "❌ Notification type not registered"
→ Demo initialization failed message
```

### Scenario C: Queue Access During Concurrent Operations
```
Multiple threads accessing same queue simultaneously
→ notify module handles with _queues_lock (thread-safe)
→ Catch and display any synchronization errors gracefully
```

### Scenario D: Invalid/Malformed Notifications
```
Notification missing expected fields
→ Try/catch AttributeError when accessing notification.message
→ Display: "⚠ Malformed notification: [details]"
```

### Scenario E: Thread Synchronization Issues
```
One player quits while other is mid-operation
→ Check threading.active_count() before sending
→ Display: "❌ Partner disconnected. Exiting..."
```

### Scenario F: Blocking Demonstration
```
Alice blocks Bob's messages
→ notify.block("alice", "bob") succeeds
→ Bob's next send is silently blocked or fails gracefully
→ Display: "⚠ Your message was blocked"
```

### Scenario G: Rate Limiting
```
User sends >100 messages rapidly
→ notify module's rate limiter triggers
→ Display: "⚠ Rate limited: Please wait before sending"
```

### Scenario H: Queue Timeout/Empty Queue
```
Check notifications when queue is empty
→ queue.get(timeout=0.1) returns None
→ Display: "✓ No pending notifications"
```

### Scenario I: One Player Exits Early (ESC or Q)
```
Alice presses ESC while Bob continues
→ Alice's thread exits immediately
→ Bob continues until round 5 or ESC
→ Display graceful exit messages for both
```

## Implementation Details

### File Structure

```
bbsengine6/py/src/bbsengine6/examples/
├── __init__.py                  ← Empty or version info
├── ping_pong_demo.py            ← Main demo script (250-300 lines)
├── README_PING_PONG.md          ← User documentation
└── PING_PONG_DEMO_PLAN.md       ← This file (planning reference)
```

### Key Code Patterns

**Pattern 1: Notification Setup**
```python
def setup_notifications():
    """Register notification types for the demo."""
    try:
        notify.register_type(
            "ping-message",
            rate_limit={"per_user": 100},
            persist=False
        )
        notify.register_type(
            "pong-message",
            rate_limit={"per_user": 100},
            persist=False
        )
        print("✓ Notification types registered")
    except Exception as e:
        print(f"❌ Failed to register notifications: {e}")
        raise
```

**Pattern 2: Thread Loop with getch()**
```python
def alice_loop():
    """Alice's game loop with getch() integration."""
    _threadlocal.moniker = "alice"
    round_num = 0
    message_log = []
    
    try:
        while round_num < MAX_ROUNDS:
            display_menu(round_num, message_log)
            
            try:
                # getch() automatically checks notifications
                key = getch.getch_str(timeout=2.0)
                
                if key in ["q", "Q"]:
                    print("\n✓ Alice quit")
                    break
                elif key == "\x1b":  # ESC
                    print("\n✓ ESC pressed - exiting demo")
                    global DEMO_EXITING
                    DEMO_EXITING = True
                    break
                elif key in ["p", "P"]:
                    send_ping("alice", round_num)
                    round_num += 1
                    message_log.append(f"[SENT] PING #{round_num}")
                elif key in ["c", "C"]:
                    check_and_display_queue("alice", message_log)
                
            except Exception as e:
                print(f"❌ Error processing input: {e}")
                continue
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        print("\n✓ Alice's game ended")
```

**Pattern 3: Send with Error Handling**
```python
def send_ping(from_moniker, round_num):
    """Send with comprehensive error handling."""
    to_moniker = "bob" if from_moniker == "alice" else "alice"
    
    try:
        # Check if recipient queue exists
        try:
            recipient_queue = notify.get_queue(to_moniker)
            if recipient_queue is None:
                print(f"❌ ERROR: {to_moniker} is not logged in")
                return False
        except Exception as e:
            print(f"❌ ERROR: Cannot access {to_moniker}'s queue: {e}")
            return False
        
        # Try to send
        try:
            notify.send(
                notification_type="ping-message",
                recipients=[to_moniker],
                template_vars={
                    "from": from_moniker,
                    "round": round_num,
                    "message": f"PING #{round_num} from {from_moniker}",
                    "timestamp": datetime.now().isoformat()
                },
                urgency="ROUTINE"
            )
            print(f"✓ Sent PING #{round_num} to {to_moniker}")
            return True
        
        except Exception as e:
            print(f"❌ ERROR: Failed to send: {e}")
            if "rate limit" in str(e).lower():
                print("   → You've sent too many messages too quickly")
            elif "blocked" in str(e).lower():
                print(f"   → {to_moniker} has blocked your messages")
            return False
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
```

**Pattern 4: Check Queue with Display**
```python
def check_and_display_queue(moniker, message_log):
    """Check and display all pending notifications."""
    try:
        queue = notify.get_queue(moniker)
        if queue is None:
            print(f"❌ Queue not found for {moniker}")
            return
        
        all_notifs = queue.get_all()
        
        if not all_notifs:
            print(f"✓ No pending notifications for {moniker}")
            return
        
        print(f"\n─── Pending Notifications for {moniker} ───")
        for notif in all_notifs:
            try:
                msg = notif.message or "No message"
                urgency = notif.urgency or "ROUTINE"
                timestamp = notif.timestamp or "unknown"
                print(f"[{urgency:8}] {timestamp} | {msg}")
                message_log.append(f"[RECEIVED] {msg}")
            except AttributeError as e:
                print(f"⚠ Malformed notification: {e}")
        
        print("──────────────────────────────────────────")
        
    except Exception as e:
        print(f"❌ ERROR checking queue: {e}")
```

## API Clarification Questions (ANSWERED)

### Q1: Template Requirement
**Decision:** Use `template_vars` with direct message passing. The `message` field in template_vars becomes the notification text. No template file needed for demo.

### Q2: Database vs In-Memory
**Decision:** Use `persist=False` for demo so notifications only stay in live memory queues. Cleaner and faster for demonstration purposes. No database setup needed.

### Q3: Moniker/Member Setup
**Decision:** Manually set `_threadlocal.moniker = "alice"` at start of each thread. This simulates a logged-in member without needing to call actual BBS login functions. This is the pattern shown in GETCH_MULTI_USER.md.

### Q4: getch() Integration
**Decision:** Call `getch.getch_str(timeout=2.0)` directly. The notification checking is built-in and automatic. No special initialization needed. getch() will automatically emit bell when notifications arrive.

### Q5: Dependencies
**Decision:** Assume bbsengine6 is installed. Add error handling for missing modules with helpful messages. Include docstring explaining requirements.

## What Demo Covers (Educational Value)

| Concept | How Demonstrated |
|---------|-----------------|
| **getch() loop integration** | Both players use getch(timeout=2.0) to detect notifications |
| **Thread-local isolation** | alice and bob have separate _threadlocal.moniker values |
| **Per-member queues** | alice's queue ≠ bob's queue, fully isolated |
| **Notification sending** | notify.send() routes to recipient's queue |
| **Notification receiving** | notify.get_queue().get_all() retrieves pending |
| **Bell emission** | getch() automatically emits bell when queue has messages |
| **Multi-user support** | Two concurrent users on same machine |
| **Error handling** | Handles 9+ failure scenarios gracefully |
| **Message logging** | Both terminal display and persistent message history |
| **Clean exit** | ESC for immediate exit, Q for local quit, round limit |
| **Keyboard input** | Full interactive control via getch_str() |

## Implementation Checklist

- [ ] Create examples/ directory structure
- [ ] Implement __init__.py
- [ ] Implement ping_pong_demo.py with all error handling
- [ ] Create README_PING_PONG.md with user guide
- [ ] Test with two concurrent terminals
- [ ] Verify all error scenarios work correctly
- [ ] Run linting and formatting (ruff)
- [ ] Create git commit

## References

- [GETCH_INTEGRATION.md](../notifyd/GETCH_INTEGRATION.md) - No daemon model, getch() checks
- [GETCH_MULTI_USER.md](../notifyd/GETCH_MULTI_USER.md) - Multi-member isolation
- notify.py API documentation (in codebase)
- getch.py implementation (in io/getch.py)
- AGENTS.md - Code style and commit guidelines
