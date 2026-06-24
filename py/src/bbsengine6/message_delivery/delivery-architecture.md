# Notification Delivery: Unified vs. Separate Path

## Current Architecture

```
Application
    ├── send() ──→ Database (writes MAC if HMAC key configured)
    ├── get_notifications() ──→ Database ──→ Notification[] (verifies MAC)
    │
    ├── UserNotificationQueue (in-process, same-process delivery)
    │
    └── Daemon (IMAP polling → email dispatch)
```

## Separation of Concerns (Current)

- **Remote/IMAP**: Client → daemon polls IMAP → dispatches via email
- **Local/TUI**: Application reads queue directly → renders locally

### Pros
- Lower latency for TUI/local users
- Works without daemon running
- HMAC verification stays client-side only — daemon doesn't need the key
- Minimal trusted surface

### Cons
- Two delivery code paths
- Notifications lost on client crash (not queued persistently)
- Harder to monitor centrally

---

## Unified Path (Daemon Always)

Route all notifications through the daemon regardless of delivery method.

### Pros
- Single delivery code path, consistent retry/logging
- Notifications survive client crashes (queued in daemon)
- Easier to monitor — all delivery goes through one place
- Better for multi-server setups (client can be stateless)

### Cons
- Added latency/complexity for TUI users (daemon round-trip)
- If daemon is down, local notifications fail too
- HMAC complexity — daemon must compute/stores MAC on send, client verifies on read

---

## HMAC Considerations

The HMAC layer protects against tampering at rest after `send()` writes to the DB. Key points:

1. **Current**: Only sender (calls `send()`) and reader (calls `get_notifications()`) need the HMAC key
2. **Unified path would require**:
   - Daemon needs HMAC key to compute/stores MAC on send
   - Client needs HMAC key to verify on read via `get_notifications()`
   - Both need the same key — larger credential surface
   - Daemon becomes a more trusted component

3. **Alternative**: Decouple computation from delivery — sender computes MAC, daemon just delivers without needing the key. But this muddies the daemon's role.

---

## When Unified Makes Sense

- Multi-server/stateless client deployments
- Need notifications to survive client restarts
- Centralized monitoring/queueing is a priority
- HMAC key can be provisioned to both daemon and clients securely

## When Separation Makes Sense

- Single-machine BBS, low-latency TUI users
- Minimal trusted surface is a priority
- Don't want to manage HMAC key on daemon
- Simplicity over robustness

---

## Decision

**Sticking with current separation for now.** The current design keeps HMAC verification local to sender/reader, avoiding credential management on the daemon. This is architecturally cleaner for single-machine deployments.

If the need arises (multi-server, persistent queuing, centralized monitoring), revisit unified path with a clear plan for HMAC key distribution.
