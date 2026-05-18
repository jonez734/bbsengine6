# How to Run the Ping/Pong Demo

## Quick Start

### Prerequisites
- Python 3.9+
- bbsengine6 installed
- Two terminal windows (for full interactive experience)

### Single Terminal (Sequential, for testing)

```bash
cd /path/to/bbsengine6/py/src
python -m bbsengine6.examples.ping_pong_demo
```

The demo will run with both players sequentially in the same terminal. Follow the prompts:
- Press Enter to start
- Type `P` to send ping/pong
- Type `C` to check pending notifications
- Type `Q` to quit local player
- Press `ESC` to exit demo immediately

### Two Terminals (Concurrent, recommended for full demo)

**Terminal 1 - Alice:**
```bash
cd /path/to/bbsengine6/py/src
python -m bbsengine6.examples.ping_pong_demo
```

**Terminal 2 - Bob:**
```bash
cd /path/to/bbsengine6/py/src
python -m bbsengine6.examples.ping_pong_demo
```

Both scripts will connect to the same shared notification system and can exchange messages in real-time.

## Interactive Controls

| Key | Action |
|-----|--------|
| `P` or `p` | Send ping/pong to other player |
| `C` or `c` | Check and display pending notifications |
| `F2` | Show pending notifications (getch() native feature) |
| `ESC` | Exit immediately (both players exit) |
| `Q` or `q` | Quit local player (other continues) |
| (timeout) | getch() automatically checks queue every 2 seconds |

## Expected Output

### Initial Screen
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
```

### Game Menu
```
═════════════════════════════════════════════════════════════
    ALICE'S PING-PONG DEMO (Moniker: ALICE)
═════════════════════════════════════════════════════════════
Round: 1/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────────────────
MESSAGE LOG:
  [Awaiting first message...]
─────────────────────────────────────────────────────────────
Queue Status: 0 pending notification(s)
═════════════════════════════════════════════════════════════
```

### After Sending Ping
```
✓ Sent PING #1 to bob


═════════════════════════════════════════════════════════════
    ALICE'S PING-PONG DEMO (Moniker: ALICE)
═════════════════════════════════════════════════════════════
Round: 1/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────────────────
MESSAGE LOG:
  [14:30:01] ✓ Sent PING #1
─────────────────────────────────────────────────────────────
Queue Status: 0 pending notification(s)
═════════════════════════════════════════════════════════════
```

### After Receiving Message
```
═════════════════════════════════════════════════════════════
    BOB'S PING-PONG DEMO (Moniker: BOB)
═════════════════════════════════════════════════════════════
Round: 1/5 | Status: Waiting for input or notification...

(P)ing / (C)heck / (Q)uit / [ESC] to exit

─────────────────────────────────────────────────────────────
MESSAGE LOG:
  [14:30:02] PING #1 from alice
─────────────────────────────────────────────────────────────
Queue Status: 1 pending notification(s)
═════════════════════════════════════════════════════════════
```

## Step-by-Step Example Session (Two Terminals)

### Terminal 1: Alice
```
$ python -m bbsengine6.examples.ping_pong_demo
✓ Notification types registered (in-memory)
✓ alice initialized (moniker=alice)
✓ bob initialized (moniker=bob)

(waits for menu display and user input)

[User presses: p]
✓ Sent PING #1 to bob

(waits for response)

(after timeout, getch auto-checks queue)
[BELL] 🔔 emits (if notification arrived)

(menu refreshes showing pending message)

[User presses: c]
─── Pending Notifications for alice ───
[ROUTINE ] 2024-05-18T14:30:00 | PONG #1 from bob
──────────────────────────────────────────
```

### Terminal 2: Bob (simultaneously)
```
$ python -m bbsengine6.examples.ping_pong_demo
✓ Notification types registered (in-memory)
✓ alice initialized (moniker=alice)
✓ bob initialized (moniker=bob)

(waits for menu, getch auto-checks)

[2 seconds pass: getch timeout occurs]
[BELL] 🔔 emits (PING arrived in bob's queue)

(menu refreshes with queue status: 1 pending)

[User presses: c]
─── Pending Notifications for bob ───
[ROUTINE ] 2024-05-18T14:30:00 | PING #1 from alice
──────────────────────────────────────────

[User presses: p]
✓ Sent PONG #1 to alice
```

## Error Scenarios You'll See

### If Bob Hasn't Logged In
```
[User presses: p]
❌ ERROR: bob is not logged in
   (Is bob logged in? Check other terminal)
Press Enter to continue...
```

### If You Exceed Rate Limit
```
❌ ERROR: Failed to send: rate limit exceeded
   → You've sent too many messages too quickly
   → Please wait a moment before sending again
Press Enter to continue...
```

### If User Disconnects
```
✓ bob: Quit
✓ bob's game ended

(alice can continue, but messages won't be received)
```

### If ESC is Pressed
```
[User presses: ESC]
✓ ESC pressed - exiting demo
✓ alice's game ended
✓ bob's game ended

╔════════════════════════════════════════════════════════════╗
║  Demo Complete!                                            ║
...
```

## Understanding What's Happening

### getch() Notification Checking
Every time `getch_str(timeout=2.0)` is called:
1. It waits up to 2 seconds for keyboard input
2. During that wait, it checks the member's notification queue
3. If a notification is found, it emits a bell (🔔)
4. If user presses F2, it displays the notifications
5. If timeout expires with no input, it returns None

### Thread-Local Member Context
- **Alice's thread** has `_threadlocal.moniker = "alice"`
- **Bob's thread** has `_threadlocal.moniker = "bob"`
- Each thread's queue is completely isolated
- No cross-member notification leakage

### In-Memory Queue (No Database)
- Notifications stored in `notify._queues[moniker]`
- `queue.put()` adds to the queue
- `queue.get()` retrieves from the queue
- `queue.get_all()` empties the queue
- All operations are thread-safe

## Troubleshooting

### "TERM environment variable not set"
This is harmless in non-interactive environments. The demo still works. In a proper terminal, you won't see this message.

### Demo hangs waiting for input
Press Enter or any key to continue. The `getch_str(timeout=2.0)` will timeout after 2 seconds.

### One terminal gets stuck
Press `ESC` in the other terminal to force exit both players.

### No bell sound
Some terminals have bell disabled. You'll still see the queue status update even without audio bell.

### Can't find the module
Make sure you're in the correct directory:
```bash
cd /path/to/bbsengine6/py/src
python -m bbsengine6.examples.ping_pong_demo
```

## Full Documentation

For comprehensive documentation including:
- Architecture diagrams
- Concept explanations
- API references
- Error handling details
- Multi-user isolation explanation

See: [README_PING_PONG.md](README_PING_PONG.md)

## Running the Test Suite

To run the comprehensive notify system tests (27 tests, all passing):

```bash
cd /path/to/bbsengine6/py/src
python testnotify.py
```

Expected output:
```
Ran 27 tests in 0.146s
OK
```

These tests verify all the APIs used by the demo.
