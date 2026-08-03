# bbsengine6 notifyd - IMAP & Event Notification System

> **STATUS (2026-07-22): SUPERSEDED.** The `notifyd` daemon
> described in this and the other 9 `BBSENGINE6_NOTIFYD_*.md`
> files was never built. Every implementation path in these
> specs routes through `bbsengine6.notify`, which was
> **deleted** in Phase 7 of `TODO-message-migration.md`
> (2026-07-22). The IMAP monitoring subsystem, the EventBus,
> the daemon process, the systemd unit, the CLI, and the
> claimed 193 tests do not exist in the codebase.
>
> **The actual bbsengine6 daemon is `bed.py` (BED = "BBS
> Engine Daemon")**, a generic WebSocket server that loads a
> router module via `--router`. See
> `py/src/bbsengine6/bed.py` (the source) and
> `py/src/bbsengine6/net/SPEC.md` (the underlying transport
> spec) for the current state.
>
> **Postoffice / IMAP work** (the closest thing to a
> replacement) is in `TODO.md` "Phase 1G: Postoffice Service
> (IMAP Polling) ✓ bed.json DONE" — that phase ships the
> `bed.json` config and the `casino/config.py` loader, but
> the actual IMAP poller is still pending.
>
> This file is preserved for historical reference only. **Do
> not implement against this spec.**

Status: NOT YET IMPLEMENTED (and superseded)
Last Updated: 2026-05-18 13:43:46

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Design Philosophy](#design-philosophy)
4. [Architecture at a Glance](#architecture-at-a-glance)
5. [Use Cases](#use-cases)
6. [Getting Started](#getting-started)

---

## Overview

### Purpose

notifyd is a daemon service that monitors IMAP mailboxes for new emails and listens for custom bbsengine6 application events, converting both into notifications delivered through the existing `bbsengine6.notify` infrastructure.

It serves as a comprehensive notification system that integrates email monitoring with application-level event handling, all unified through bbsengine6's notification framework.

### Scope

notifyd handles:

- **IMAP Email Monitoring**: Polling multiple IMAP servers and mailboxes for new emails
- **Custom Event Firing**: Application events (login, logout, game events) triggered from bbsengine6 code
- **Notification Dispatch**: Routing all notifications through `bbsengine6.notify.send()`
- **State Tracking**: PostgreSQL-based storage of IMAP UIDs and notification history
- **Credential Management**: Secure hybrid credential handling (env vars → keyring → prompt)
- **Systemd Integration**: Daemon managed as a system service with auto-restart and journaling

---

## Key Features

- **IMAP Monitoring**: Poll configured IMAP servers for new emails, avoid duplicates, send notifications to users
- **Event Listening**: Listen for bbsengine6 application events (login, logout, game events) via custom event hook system
- **Notification Dispatch**: Route all notifications through `bbsengine6.notify.send()`
- **State Tracking**: PostgreSQL database stores last-seen email UIDs and notification history
- **Credential Management**: Hybrid credential storage (environment variables, keyring, user prompt)
- **Systemd Integration**: Daemon managed as system service with auto-restart and journal logging
- **Configuration**: JSON configuration files with environment variable substitution
- **Multi-server Support**: Monitor multiple IMAP accounts simultaneously
- **Graceful Degradation**: Individual server failures don't crash the daemon
- **RFC822 Parsing**: Handles complex email formats with proper encoding

---

## Design Philosophy

- **Threading-based concurrency**: Match bbsengine6's `getch()` polling pattern
- **Graceful degradation**: Fail individual servers/events without crashing daemon
- **Separation of concerns**: Event hooks decoupled from IO event system
- **Existing infrastructure**: Use bbsengine6's notify module, database pool, configuration patterns
- **Security**: No hardcoded credentials, hybrid keyring + env var support

---

## Architecture at a Glance

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

### Threading Model

| Thread | Purpose | Polling Pattern | Lifecycle |
|--------|---------|-----------------|-----------|
| Main | Daemon control, signal handling, thread coordination | N/A | Infinite loop until SIGTERM |
| IMAP Monitor | Poll servers, detect new emails | Every 30s (configurable) | Spawned at start, joined at stop |
| Event Listener | Registered handlers, fire custom events | Event-driven | Spawned at start, runs passively |

**Key Property**: Neither background thread blocks main thread. Daemon stays responsive to signals.

---

## Use Cases

### Email Notification Hub

Monitor multiple email accounts and route notifications to different teams:

```
Gmail Account → newmail notifications → Security Team
Corporate Exchange → system-alerts → DevOps Team
Support Ticketing → incoming-tickets → Support Team
```

### Application Event System

Fire custom events from bbsengine6 code and notify interested parties:

```
User Login → fire_event("user.login") → Admin Notifications
Game Combat → fire_event("game.combat") → Combat Log
File Upload → fire_event("file.upload") → Audit Log
```

### Integrated Multi-Source Alerting

Combine email and application events into a unified notification queue:

- Email notifications appear as message arrivals
- Application events trigger custom notifications
- All routed through bbsengine6's notification system
- Users see everything during `getch()` calls

---

## Getting Started

### Quick Start (Event-Only)

For BBS systems that only need application event notifications, without IMAP:

1. Create minimal configuration file
2. Fire events from bbsengine6 code using `notifyd.fire_event()`
3. Users see notifications during `getch()` calls

### Full Setup (With IMAP Monitoring)

For systems that also want to monitor email:

1. Configure IMAP servers in JSON
2. Set up credentials (env vars or keyring)
3. Create notification templates
4. Run as systemd service
5. Fire custom events as needed

### Recommended for BBS: getch() Integration

Instead of running a separate daemon, use bbsengine6's existing `getch()` integration:

- No persistent background process needed
- Notifications checked during keyboard input
- Native per-member isolation
- Built-in to bbsengine6's architecture

---

## Next Steps

For detailed information, see:

- [BBSENGINE6_NOTIFYD_ARCHITECTURE.md](BBSENGINE6_NOTIFYD_ARCHITECTURE.md) - System design and threading model
- [BBSENGINE6_NOTIFYD_CONFIGURATION.md](BBSENGINE6_NOTIFYD_CONFIGURATION.md) - Configuration options and examples
- [BBSENGINE6_NOTIFYD_DEPLOYMENT.md](BBSENGINE6_NOTIFYD_DEPLOYMENT.md) - Installation and deployment models
- [BBSENGINE6_NOTIFYD_COMPONENTS.md](BBSENGINE6_NOTIFYD_COMPONENTS.md) - Component specifications and API
- [BBSENGINE6_NOTIFYD_DATABASE.md](BBSENGINE6_NOTIFYD_DATABASE.md) - Database schema and state tracking
- [BBSENGINE6_NOTIFYD_INTEGRATION.md](BBSENGINE6_NOTIFYD_INTEGRATION.md) - Integration with bbsengine6 infrastructure
- [BBSENGINE6_NOTIFYD_TESTING.md](BBSENGINE6_NOTIFYD_TESTING.md) - Testing strategy and coverage
- [BBSENGINE6_NOTIFYD_DESIGN_DECISIONS.md](BBSENGINE6_NOTIFYD_DESIGN_DECISIONS.md) - Design rationale and tradeoffs
- [BBSENGINE6_NOTIFYD_DEPENDENCIES.md](BBSENGINE6_NOTIFYD_DEPENDENCIES.md) - Dependencies and compatibility

---

**Note**: This specification describes the notifyd system architecture and design. The implementation status is indicated in the Status line above. For implementation details and deployment guides, see the related documents.
