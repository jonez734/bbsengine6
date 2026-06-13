# bbsengine6 notifyd - Architecture

Status: NOT YET IMPLEMENTED
Last Updated: 2026-05-18 13:43:46

---

## Table of Contents

1. [System Components](#system-components)
2. [Threading Model](#threading-model)
3. [Package Structure](#package-structure)
4. [Data Flow](#data-flow)
5. [Deployment Models](#deployment-models)

---

## System Components

### Daemon Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   notifyd Daemon                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Main Thread (Daemon Lifecycle)                  │   │
│  │  - Config loading                               │   │
│  │  - Signal handling (SIGTERM, SIGINT)           │   │
│  │  - Thread spawning & coordination               │   │
│  └──────────────────────────────────────────────────┘   │
│                         │                                │
│         ┌───────────────┼───────────────┐               │
│         │               │               │               │
│  ┌──────▼──────┐ ┌─────▼─────┐ ┌──────▼──────┐        │
│  │ Monitor     │ │ Event     │ │ Database    │        │
│  │ Thread      │ │ Listener  │ │ Thread      │        │
│  │             │ │ Thread    │ │ (implicit)  │        │
│  │ Polls IMAP  │ │ Fires     │ │             │        │
│  │ servers     │ │ handlers  │ │ psycopg3    │        │
│  │ every 30s   │ │           │ │ connection  │        │
│  └──────┬──────┘ └─────┬─────┘ │ pool        │        │
│         │              │       └─────────────┘        │
│         └──────────────┼──────────┐                   │
│                        │          │                   │
│         ┌──────────────▼──────────▼───┐              │
│         │  NotificationDispatcher     │              │
│         │  - Calls notify.send()      │              │
│         │  - Records to DB            │              │
│         │  - Handles errors           │              │
│         └──────────────┬───────────────┘              │
│                        │                              │
│                        ▼                              │
│         ┌──────────────────────────┐                 │
│         │  bbsengine6.notify       │                 │
│         │  - Templates             │                 │
│         │  - Rate limiting         │                 │
│         │  - User delivery         │                 │
│         └──────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

### Component Overview

1. **Main Thread**: Daemon lifecycle management, signal handling, thread coordination
2. **IMAP Monitor Thread**: Continuously polls IMAP servers for new emails
3. **Event Listener Thread**: Registers and manages event handlers
4. **Notification Dispatcher**: Routes notifications to bbsengine6.notify
5. **Database Connection Pool**: Manages PostgreSQL connections (via bbsengine6.database)

---

## Threading Model

| Thread | Purpose | Polling Pattern | Lifecycle |
|--------|---------|-----------------|-----------|
| Main | Daemon control, signal handling, thread coordination | N/A | Infinite loop until SIGTERM |
| IMAP Monitor | Poll servers, detect new emails | Every 30s (configurable) | Spawned at start, joined at stop |
| Event Listener | Registered handlers, fire custom events | Event-driven | Spawned at start, runs passively |

### Key Properties

- Neither background thread blocks main thread
- Daemon stays responsive to signals (SIGTERM, SIGINT)
- Graceful shutdown: SIGTERM → stop event loop → join threads → exit
- Non-daemon threads ensure clean exit on process termination

---

## Package Structure

### Location

`bbsengine6.notifyd` - Submodule within bbsengine6 Python package

### Directory Layout

```
bbsengine6/py/src/bbsengine6/notifyd/
│
├── __init__.py                    # Public API exports
│
├── config.py                      # Configuration loading & validation
│   - NotifydConfig dataclass
│   - ImapServer dataclass
│   - Config loading from JSON + env vars
│
├── credentials.py                 # Credential management
│   - CredentialManager class
│   - Env var, keyring, prompt support
│   - Hybrid storage strategy
│
├── storage.py                     # PostgreSQL state tracking
│   - NotificationStorage class
│   - IMAP UID tracking
│   - Notification history
│   - Database schema management
│
├── imap_monitor.py                # IMAP polling logic
│   - ImapMonitor class
│   - Server polling
│   - Email parsing & duplicate detection
│   - Notification triggering
│
├── hooks.py                       # Custom event hook system
│   - EventBus class
│   - fire_event() function
│   - register_event_handler() function
│
├── event_listener.py              # Event handler registration
│   - EventListener class
│   - Hook registration from config
│   - Integration with io.KeyEventSystem (optional)
│
├── notification.py                # Notification dispatch
│   - NotificationDispatcher class
│   - Integration with bbsengine6.notify
│   - Error handling & logging
│
├── daemon.py                      # Main daemon process
│   - NotifyDaemon class
│   - Thread lifecycle management
│   - Graceful shutdown
│   - PID file management
│
├── cli.py                         # Command-line interface
│   - main() entry point
│   - Argument parsing
│   - Test commands (--test-imap, --test-notify)
│   - Logging setup
│
└── tests/
    ├── __init__.py
    ├── test_config.py             # Config loading, env var substitution
    ├── test_credentials.py        # Credential retrieval (mocked keyring)
    ├── test_storage.py            # PostgreSQL operations (test DB)
    ├── test_imap_monitor.py       # Email detection (mocked IMAP)
    ├── test_event_listener.py     # Handler registration/firing
    ├── test_notification.py       # notify.send() integration (mocked)
    └── test_daemon.py             # Thread lifecycle, graceful shutdown
```

---

## Data Flow

### IMAP Email Path

```
IMAP Server
    ↓
ImapMonitor.poll() (every 30s)
    ↓
Fetch new emails (UID > last_uid)
    ↓
Parse RFC822 format
    ↓
NotificationDispatcher.send_imap_notification()
    ↓
bbsengine6.notify.send()
    ↓
User Notification Queue
    ↓
Display in getch()
```

### Application Event Path

```
Application Code
    ↓
notifyd.fire_event("event-name", {...data...})
    ↓
EventBus.fire() → registered handlers
    ↓
EventListener.on_event()
    ↓
NotificationDispatcher.send_custom_notification()
    ↓
bbsengine6.notify.send()
    ↓
User Notification Queue
    ↓
Display in getch()
```

### Complete Message Flow

```
┌─────────────────────────────┐
│   Source                    │
├─────────────────────────────┤
│ IMAP Server OR Application  │
└──────────────┬──────────────┘
               │
               ↓
┌──────────────────────────────┐
│ Monitoring/Event System      │
├──────────────────────────────┤
│ ImapMonitor / EventListener  │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────────┐
│ Data Collection                  │
├──────────────────────────────────┤
│ Parse email / Get event data     │
└──────────────┬───────────────────┘
               │
               ↓
┌──────────────────────────────┐
│ Notification Dispatch        │
├──────────────────────────────┤
│ NotificationDispatcher       │
│ - Build template vars        │
│ - Call notify.send()         │
│ - Record to history          │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│ bbsengine6.notify            │
├──────────────────────────────┤
│ - Apply templates            │
│ - Rate limiting              │
│ - Route to recipients        │
│ - Add to notification queue  │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│ User Notification Queue      │
├──────────────────────────────┤
│ Pending notifications        │
└──────────────┬───────────────┘
               │
               ↓
┌──────────────────────────────┐
│ getch() Checks Queue         │
├──────────────────────────────┤
│ - Emits bell if notifications
│ - F2 displays notifications  │
└──────────────────────────────┘
```

---

## Deployment Models

### Model 1: Traditional Daemon (Full Feature Set)

**Architecture:**
```
Background daemon process continuously runs
    ↓
Polls IMAP servers every 30 seconds
    ↓
Fires custom events from application code
    ↓
All notifications routed through bbsengine6.notify
    ↓
Users see notifications in getch()
```

**Advantages:**
- Continuous IMAP monitoring without additional setup
- Always-on monitoring for critical alerts
- Desktop email client use case compatible

**Disadvantages:**
- Persistent background process consuming resources
- Separate lifecycle from BBS application
- More complex deployment (systemd service)

**When to Use:**
- Need continuous email monitoring
- Desktop email notification scenario
- Monitoring 24/7 for critical alerts

### Model 2: getch() Integration (Recommended for BBS)

**Architecture:**
```
User calls getch() during menu navigation
    ↓
getch() checks notification queue
    ↓
Application code fires events via notifyd.fire_event()
    ↓
Events added to notification queue
    ↓
User sees notifications during getch()
```

**Advantages:**
- No persistent background daemon needed
- Fits BBS terminal paradigm perfectly
- Minimal resource overhead
- Built-in per-member notification isolation
- Event-driven (perfect for application events)
- Simple deployment (just configuration)

**Disadvantages:**
- IMAP polling requires external scheduler (cron/systemd-timer)
- Only checks notifications during user interaction

**When to Use:**
- BBS with users at terminal
- Event-based notifications only
- Want to minimize resource usage
- Prefer integrated solution

### Model 3: Scheduled IMAP Polling (Hybrid)

**Architecture:**
```
Cron job or systemd timer (every 5 minutes)
    ↓
Runs notifyd poll-imap command
    ↓
Polls IMAP servers once
    ↓
Results added to notification queue
    ↓
Custom events from application code
    ↓
Users see all notifications in getch()
```

**Advantages:**
- Email monitoring without persistent daemon
- Configurable schedule (e.g., business hours only)
- Low resource usage
- BBS-friendly

**Disadvantages:**
- Scheduled polling has latency (e.g., 5-minute delays)
- Not suitable for time-critical alerts

**When to Use:**
- Want email monitoring without daemon overhead
- Acceptable to have 5-minute latency
- Prefer scheduled polling

### Comparison Matrix

| Feature | Daemon Model | getch() Model | Scheduled Polling |
|---------|--------------|---------------|-------------------|
| **Continuous polling** | ✅ Yes | ❌ No | ❌ Scheduled only |
| **Always-on monitoring** | ✅ Yes | ❌ No | ❌ At schedule time |
| **Complexity** | High | Low | Medium |
| **BBS-friendly** | Good | Better | Good |
| **Event firing** | ✅ Works | ✅ Works | ✅ Works |
| **IMAP monitoring** | ✅ Built-in | ⚠️ Requires cron | ⚠️ Cron-based |
| **Resource usage** | Higher | Minimal | Low |
| **Deployment** | Systemd service | Configuration | Cron + config |

---

## Recommended Architecture for bbsengine6

### Use getch() Integration Model because:

1. ✅ **Fits BBS paradigm** - Notifications during user interaction
2. ✅ **Minimal overhead** - No persistent background process
3. ✅ **Already implemented** - getch() has notification support built-in
4. ✅ **Event-driven** - Perfect for application events (login, messages, etc.)
5. ✅ **Simple deployment** - Just configuration file
6. ✅ **Scales better** - No thread per concurrent user
7. ✅ **Native isolation** - Per-member notification queues in bbsengine6.notify
8. ✅ **Debugging** - Everything synchronous during getch()

For IMAP monitoring, use scheduled polling via cron or systemd timer if needed, but focus on application events for immediate notifications.

---

For detailed component specifications, see [BBSENGINE6_NOTIFYD_COMPONENTS.md](BBSENGINE6_NOTIFYD_COMPONENTS.md).

For deployment and configuration, see [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](BBSENGINE6_NOTIFYD_DEPLOYMENT.md).
