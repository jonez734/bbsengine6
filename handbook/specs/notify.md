# bbsengine6.notify Specification

> **STATUS (2026-07-22): SUPERSEDED.** The `bbsengine6.notify` package
> was **deleted** in Phase 7 of `TODO-message-migration.md`. The
> `engine.__notify*` tables, `engine.notify*` views,
> `checknotify.py` / `checknotifyd.py` modules, and the entire
> `notify` / `message_delivery` Python package have all been
> removed. The replacement is `bbsengine6/message.py`; see
> `TODO-message-migration.md` Phase 8 for the live behavior.
>
> **Note (Phase 11, 2026-09-01):** The `bbsengine6/message.py`
> reference above is shorthand for the `bbsengine6/message/`
> package. Post-Phase-11 the package is layered (`service`,
> `dal/`, `templates`, `cache`); `bbsengine6/message/lib.py` is a
> thin facade. The package-level surface is unchanged.
>
> The recipient-validation / group-management features documented
> in `NOTIFY_MESSAGING.md` (and the `moniker_exists` /
> `group_exists` / `get_group_members` functions) were preserved
> and live in `py/src/bbsengine6/member/lib.py` (see
> `handbook/specs/member.md` "Recipient Validation & Group
> Management (v1.0)").
>
> **Confusingly-named sibling project:** the `BBSENGINE6_NOTIFYD_*.md`
> files in `handbook/specs/` describe a separate "notifyd"
> daemon that was never built. They are also marked SUPERSEDED.
> The actual bbsengine6 daemon is `py/src/bbsengine6/bed.py`
> (BED = "BBS Engine Daemon"), a generic WebSocket server that
> loads a router module via `--router`; see
> `py/src/bbsengine6/net/SPEC.md` "BED Daemon" for the live
> reference.
>
> This spec is preserved for historical reference only. **Do not
> implement against this spec** — the tables, the Python package,
> and the SQL files referenced here no longer exist.

## Summary

`notify.py` provides a robust, thread-safe user notification system for broadcasting events to specific users or groups with templating, urgency levels, rate limiting, and blocking support. Notifications are delivered both live (in-memory queues) and persistently (database storage).

## Connection Management

All notify functions accept `args`, `pool`, and `conn` kwargs for database connection management:

```python
def send(
    notification_type: str,
    recipients: List[str],
    template: str,
    template_vars: Optional[Dict[str, Any]] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: Optional[NotificationUrgency] = None,
    should_persist: bool = True,
    args: Optional[Any] = None,
    **kwargs,
) -> Notification
```

**Connection Priority:**
1. `conn` - Use provided connection (caller manages lifecycle)
2. `pool` - Get connection from pool (returned to pool in finally)
3. `args` - Get pool from args, connection from pool (returned to pool in finally)
4. Falls back to `BBSENGINE6_DBNAME` env var if none provided

**Example:**
```python
# Option 1: Use args (creates pool from args, returns connection)
notify.send(..., args=args)

# Option 2: Use pool (get connection from pool, return it)
notify.send(..., pool=pool)

# Option 3: Use conn (caller manages lifecycle, not closed)
notify.send(..., conn=conn)

# Option 4: No connection args - uses BBSENGINE6_DBNAME env var
notify.send(...)
```

## Brief Description

A standalone notification module enabling game logic and application code to send targeted notifications to users with:
- Single unified `notify.send()` function with flexible recipient targeting
- Safe template-based messaging with variable substitution
- Dynamically registered notification types with configurable rate limits
- Dual delivery: live queues for active sessions + database persistence
- Comprehensive input validation and security (moniker validation, template safety, rate limiting)
- One-way blocking: recipients can block senders
- Freeform group targeting with `@group_name` syntax
- Special `@everyone` support (magic expansion to active sessions, or explicit group)
- Urgency levels (ROUTINE, IMPORTANT, URGENT, CRITICAL)
- Full audit trail (creation, delivery, read timestamps)
- Database-accessible rate limits for website integration

## Thread Safety

### Safe

- **`notify.send()`** -- Thread-safe. Uses atomic queue operations and database transactions. Multiple threads can call simultaneously.
- **`notify.get_notifications()`, `notify.get_queue()`** -- Thread-safe reads from database and in-memory queues.
- **`notify.mark_read()`, `notify.mark_delivered()`** -- Thread-safe database updates.
- **`notify.block()`, `notify.unblock()`, `notify.is_blocked()`** -- Thread-safe blocking checks and updates.
- **`notify.register_type()`** -- Thread-safe type registration (registers once, checked before database insert).
- **`UserNotificationQueue`** -- Uses `queue.Queue[Notification]` which is thread-safe by design.

### Not Thread-Safe (Don't Call These)

- **None.** All public APIs are thread-safe. The system is designed for concurrent access from multiple application threads.

## Public API

### Core Send Function (Single Unified Function)

```python
def send(
    notification_type: str,
    recipients: List[str],
    template: str,
    template_vars: Optional[Dict[str, Any]] = None,
    sender_moniker: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    urgency: Optional[NotificationUrgency] = None,
    should_persist: bool = True,
) -> Notification
```

Send notification to flexible recipient list. Auto-registers notification type if not exists. Returns rendered `Notification` object.

**Parameters:**
- `notification_type`: Type identifier (e.g., "EMPYRE_VICTORY", "USER_MESSAGE"). Alphanumeric + underscore only. Max 50 chars. Auto-registers on first use.
- `recipients`: List of recipient targets (mixed format allowed):
  - `"moniker"` - specific user (e.g., `"jam"`, `"alice"`)
  - `"@group_name"` - group members (e.g., `"@guild:dragons"`, `"@faction:empire"`)
  - `"@everyone"` - special: expands to all active users from sessions (magic) OR explicit group if exists
  - Can mix: `["jam", "alice", "@guild:dragons"]`
- `template`: Message template with `{variable}` placeholders. Max 500 chars. Only supports `{name}` syntax, no expressions.
- `template_vars`: Dict of variables to substitute. Values must be string/int/float. Max 100 chars per string, 10KB total.
- `sender_moniker`: Optional sender username (None = system). Validated if provided.
- `data`: Optional structured data for programmatic use. Max 10KB JSON.
- `urgency`: `NotificationUrgency` enum (ROUTINE, IMPORTANT, URGENT, CRITICAL). Defaults to type's default_urgency.
- `should_persist`: If True, store in database for later retrieval.

**Returns:** `Notification` object with rendered message and error tracking.

**Raises:**
- `ValueError`: Invalid template or type name.

**Note on Invalid Recipients:** If recipient doesn't exist (invalid moniker or non-existent group), the error is logged and the recipient is skipped. Send continues with valid recipients. Errors are tracked in the returned `Notification` object.

**Recipient Resolution:**
1. If recipient starts with `@`:
   - Special case `@everyone`:
     - Check if explicit `@everyone` group exists in `__notify_group`
     - If yes: expand to group members
     - If no: query `__session` for active sessions, get distinct monikers (magic expansion)
   - Other `@group_name`:
     - Query `__notify_group` where group_name matches
     - If group doesn't exist: **log error, skip recipient, continue**
2. If recipient doesn't start with `@`:
   - Treat as direct moniker
   - Validate exists in `__member` table
   - If doesn't exist: **log error, skip recipient, continue**

**Examples:**
```python
# Send to specific user
notify.send(
    notification_type="EMPYRE_VICTORY",
    recipients=["jam"],
    template="You defeated {opponent}! Earned {credits} credits.",
    template_vars={"opponent": "barbarians", "credits": 500},
    urgency=NotificationUrgency.URGENT,
    data={"game": "empyre", "opponent_id": "barbarians"}
)

# Send to group
notify.send(
    notification_type="GUILD_ANNOUNCEMENT",
    recipients=["@guild:dragons"],
    template="Guild meeting in {minutes} minutes!",
    template_vars={"minutes": 5},
    urgency=NotificationUrgency.IMPORTANT
)

# Send to all active users (magic @everyone)
notify.send(
    notification_type="SYSTEM_MAINTENANCE",
    recipients=["@everyone"],
    template="Server maintenance in {minutes} minutes. Save progress!",
    template_vars={"minutes": 5},
    urgency=NotificationUrgency.CRITICAL,
    should_persist=False
)

# Send to mixed recipients
notify.send(
    notification_type="TOURNAMENT",
    recipients=["jam", "alice", "@guild:dragons", "@faction:empire"],
    template="Tournament event: {event}",
    template_vars={"event": "Joust Battle Royale"},
    urgency=NotificationUrgency.IMPORTANT
)

# Invalid group (logs error, sends to valid recipients)
notify.send(
    notification_type="TEST",
    recipients=["jam", "@invalid_group"],
    template="Testing..."
    # Result: jam receives notification
    #         @invalid_group logs error and is skipped
    #         Notification returned with error tracking:
    #         recipients_ok: ["jam"]
    #         recipients_failed: ["@invalid_group"]
    #         errors: {"@invalid_group": "Group does not exist"}
)

# From application code
from bbsengine6 import notify

# Empyre game victory
notify.send(
    notification_type="EMPYRE_VICTORY",
    recipients=["jam"],
    template="You defeated {opponent}!",
    template_vars={"opponent": "barbarians"},
    urgency=notify.NotificationUrgency.URGENT,
    data={"opponent_id": "barbarians", "reward": 500}
)

# Social feature - post shared
notify.send(
    notification_type="POST_SHARED",
    recipients=["jam"],
    sender_moniker="alice",
    template="{sender} shared a post: {title}",
    template_vars={"sender": "alice", "title": "Check this out!"},
    urgency=notify.NotificationUrgency.IMPORTANT,
    data={"post_id": 12345}
)

# Joust request
notify.send(
    notification_type="JOUST_REQUEST",
    recipients=["jam"],
    sender_moniker="bob",
    template="{sender} wants to joust you!",
    template_vars={"sender": "bob"},
    urgency=notify.NotificationUrgency.IMPORTANT,
    data={"requester_moniker": "bob", "joust_id": 99}
)
```

### Consumption Functions

```python
def get_notifications(
    moniker: str,
    limit: int = 10,
    offset: int = 0,
    args: Optional[Any] = None,
    **kwargs,
) -> List[Notification]
```
Retrieve notifications for a user from database. All notifications (read and unread).

**Parameters:**
- `moniker`: User moniker.
- `limit`: Max notifications to return (default 10).
- `offset`: Number to skip (for pagination, default 0).
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Returns:** List of `Notification` objects, newest first.

---

```python
def get_queue(moniker: str) -> UserNotificationQueue
```
Get the in-memory notification queue for active user sessions. No database connection needed.

**Returns:** `UserNotificationQueue` object. Caller can `.get(timeout=1.0)` to block until notification arrives.

**Example:**
```python
queue = notify.get_queue("jam")
while True:
    notification = queue.get(timeout=5.0)  # Blocks until notification
    if notification:
        show_popup(notification.message)
        notify.mark_read(notification.id, "jam")
```

---

```python
def count(moniker: str, args: Optional[Any] = None, **kwargs) -> int | None
```
Get total notification count for user from database.

**Parameters:**
- `moniker`: User moniker.
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Returns:** Total count, or None if connection unavailable.

---

```python
def get_urgent(moniker: str, args: Optional[Any] = None, **kwargs) -> List[Notification]
```
Get urgent (URGENT or CRITICAL) notifications for user.

**Returns:** List of high-priority `Notification` objects.

---

```python
def mark_read(notification_id: int, moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Mark notification as read by user. Updates database and removes from queue.

**Parameters:**
- `notification_id`: Notification ID.
- `moniker`: User moniker.
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Raises:**
- `ValueError`: Invalid notification_id or moniker.

---

```python
def mark_delivered(notification_id: int, moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Mark notification as delivered to user (internal use). Called when notification added to live queue.

### Type Management Functions

```python
def register_type(
    type_name: str,
    default_urgency: NotificationUrgency = NotificationUrgency.ROUTINE,
    max_per_hour: int = 10,
    persist_by_default: bool = True,
    args: Optional[Any] = None,
    **kwargs,
) -> None
```
Explicitly register a notification type with rate limits. Optional; types auto-register on first send with defaults.

**Parameters:**
- `type_name`: Type identifier (alphanumeric + underscore, max 50 chars).
- `default_urgency`: Default urgency if not specified in send call.
- `max_per_hour`: Rate limit (default 10/hour).
- `persist_by_default`: Whether to persist to DB by default.
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Raises:**
- `ValueError`: Type already registered or invalid type_name.

**Example:**
```python
notify.register_type(
    type_name="EMPYRE_VICTORY",
    default_urgency=notify.NotificationUrgency.URGENT,
    max_per_hour=50,  # Battles can happen frequently
    persist_by_default=True
)
```

---

```python
def get_types(args: Optional[Any] = None, **kwargs) -> Dict[str, Dict]
```
Get all registered notification types and their settings.

**Parameters:**
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Returns:** Dict mapping type_name to {default_urgency, max_per_hour, persist_by_default}.

---

```python
def set_rate_limit(type_name: str, max_per_hour: int, args: Optional[Any] = None, **kwargs) -> None
```
Change rate limit for a notification type at runtime.

**Parameters:**
- `type_name`: Notification type name.
- `max_per_hour`: New rate limit.
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

### Group Management Functions

```python
def create_group(
    group_name: str,
    member_monikers: Optional[List[str]] = None,
    args: Optional[Any] = None,
    **kwargs,
) -> None
```
Create a new notification group.

**Parameters:**
- `group_name`: Freeform group name (max 100 chars). Can include special names like "@everyone".
- `member_monikers`: Initial members (optional).
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Example:**
```python
notify.create_group("@guild:dragons", member_monikers=["jam", "alice", "bob"])
notify.create_group("@everyone", member_monikers=[...])  # Explicit @everyone
```

---

```python
def add_to_group(group_name: str, moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Add user to group.

---

```python
def remove_from_group(group_name: str, moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Remove user from group.

---

```python
def get_group_members(group_name: str, args: Optional[Any] = None, **kwargs) -> List[str]
```
Get all members of a group.

### Blocking Functions (One-Way)

```python
def block(blocker_moniker: str, sender_moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Block notifications from sender to blocker (one-way). Blocker won't see sender's future notifications.

**Parameters:**
- `blocker_moniker`: User doing the blocking (validated).
- `sender_moniker`: User being blocked (validated).
- `args`: Application args with databasename.
- `**kwargs`: `pool` or `conn` for database connection.

**Effect:** `sender_moniker` can no longer send notifications that `blocker_moniker` will receive. Blocker won't see them in their queue or in new unread notifications.

**Note:** This does NOT prevent `blocker_moniker` from sending to `sender_moniker`.

**Example:**
```python
# jam blocks alice
notify.block("jam", "alice")
# Result: alice can still send to jam, but jam won't see alice's notifications
```

---

```python
def unblock(blocker_moniker: str, sender_moniker: str, args: Optional[Any] = None, **kwargs) -> None
```
Remove a block.

---

```python
def is_blocked(sender_moniker: str, recipient_moniker: str, args: Optional[Any] = None, **kwargs) -> bool
```
Check if sender's notifications to recipient are blocked (one-way check).

**Returns:** True if recipient has blocked sender.

---

```python
def get_blocked(moniker: str, args: Optional[Any] = None, **kwargs) -> List[str]
```
Get list of all monikers that have blocked this user.

---

```python
def expunge(notification_id: int, args: Optional[Any] = None, **kwargs) -> bool
```
Hard-delete a notification and all its recipients via CASCADE.

**Returns:** True if successful, False otherwise.

## Input Validation

All user input is validated comprehensively at entry points:

### Moniker Validation
- Must exist in user database
- Case-sensitive
- Max 255 chars
- Alphanumeric + underscore + dash only
- No empty strings
- Raises `ValueError` if invalid

### Recipient Format Validation
- Monikers: validated as above
- Groups: `@group_name` format validated
- Special: `@everyone` always allowed
- Invalid groups/monikers: logged and skipped (non-fatal)

### Template Validation
- Only `{variable_name}` syntax allowed (no expressions, no `{name[0]}`, no method calls)
- Max 500 chars
- Variables must be defined in `template_vars`
- Each variable used in template must exist in vars dict
- Extra variables in dict are ignored (OK)
- Raises `ValueError` if syntax invalid or vars mismatch

### Template Variables
- Keys: alphanumeric + underscore (no special chars)
- Values: string (max 100 chars), int, or float only
- Total dict size: max 10KB
- No nested dicts/lists
- Raises `ValueError` if type invalid

### Notification Type
- Alphanumeric + underscore only
- Max 50 chars
- No empty strings
- Auto-registers if not exists (with defaults)
- Raises `ValueError` if invalid format

### Group Names
- Freeform strings (no validation beyond length)
- Max 100 chars
- Auto-create if not exists
- No special restrictions (can include `@` prefix)

### Rate Limiting
- Per (sender_moniker, notification_type) pair
- Checked at send time
- Raises `RuntimeError` with remaining time if exceeded

### Blocking (One-Way)
- Only recipient can block sender
- Blocks are directional: A blocks B does NOT mean B blocks A
- Checked at delivery time
- Blocked notifications still stored in DB but marked as blocked
- Blocker won't retrieve blocked notifications via `get_notifications()`

## Data Structures

### Notification (dataclass)

```python
@dataclass
class Notification:
    id: int                               # bigserial from DB
    notification_type: str                # Registered type
    recipients: List[str]                 # Original recipients list
    recipients_ok: List[str]             # Successfully notified
    recipients_failed: List[str]         # Failed to resolve
    sender_moniker: Optional[str]         # Who triggered (None=system)
    template: str                         # Message template
    template_vars: Dict[str, Any]         # Template variables
    message: str                          # Rendered message
    data: Dict[str, Any]                 # Structured data
    urgency: NotificationUrgency          # ROUTINE/IMPORTANT/URGENT/CRITICAL
    timestamp: float                      # Unix timestamp
    
    # Tracking per recipient
    read_by: Dict[str, float]            # {"jam": 1234567890.5}
    delivered_to: Dict[str, float]       # {"jam": 1234567890.0}
    blocked_from: Set[str]               # {"jam"} - blocked recipients
    
    # Error tracking
    errors: Dict[str, str]               # {"@invalid_group": "Group does not exist"}
    
    should_persist: bool
    created_at: datetime
```

### NotificationUrgency (Enum)

```python
class NotificationUrgency(Enum):
    ROUTINE = "ROUTINE"      # Show in list, no interruption
    IMPORTANT = "IMPORTANT"  # May highlight or show indicator
    URGENT = "URGENT"        # Show immediately to active users
    CRITICAL = "CRITICAL"    # Interrupt input, show popup
```

### UserNotificationQueue

```python
class UserNotificationQueue:
    def put(self, notification: Notification) -> None
    def get(self, timeout: float = None) -> Notification | None
    def get_all() -> List[Notification]
    def peek_urgent(self) -> Notification | None
    def has_urgent(self) -> bool
    def size(self) -> int
```

Thread-safe queue for active user sessions. Uses Python's `queue.Queue` internally.

## Database Schema

### Tables (7 total)

1. **`engine.__notify`** - Core notification storage
   - `id` (bigserial)
   - `notification_type`, `sender_moniker`, `template`, `template_vars`
   - `rendered_message`, `data`, `urgency`, `should_persist`
   - `datecreated`, `createdbymoniker`
   - Indexes: type, created, data (GIN), sender

2. **`engine.__notify_recipient`** - Per-recipient tracking
   - `notify_id` (FK → __notify)
   - `recipient_moniker` (FK → __member)
   - `sessionid` (FK → __session, optional for live delivery)
   - `is_blocked`, `datedelivered`, `dateread`, `datecreated`
   - PK: (notify_id, recipient_moniker)
   - Indexes: moniker, read (partial), blocked (partial), session

3. **`engine.__notify_block`** - One-way blocking
   - `blocker_moniker` (FK → __member)
   - `sender_moniker` (FK → __member)
   - `datecreated`, `createdbymoniker`
   - PK: (blocker_moniker, sender_moniker)
   - Indexes: sender

4. **`engine.__notify_group`** - Group membership
   - `group_name` (text)
   - `member_moniker` (FK → __member)
   - `dateadded`, `addedbymoniker`
   - PK: (group_name, member_moniker)
   - Indexes: member, group_name

5. **`engine.__notify_type`** - Type registration and rate limits
   - `type_name` (text PK)
   - `default_urgency` (ENUM)
   - `max_per_user_per_hour` (int)
   - `persist_by_default` (boolean)
   - `dateregistered`, `registeredbymoniker`

6. **`engine.__notify_rate_limit`** - Per-user rate limit tracking
   - `sender_moniker`, `notification_type` (composite PK)
   - `send_count` (int)
   - `window_start` (timestamptz)
   - `last_updated` (timestamptz)
   - Indexes: window_start (for cleanup)

### Views (4 total)

1. **`engine.notify`** - Main join view (notify + notify_recipient)
   - Includes timezone-aware local timestamps
   - Epoch timestamps for API compatibility

2. **`engine.notify_unread`** - Unread notifications only

3. **`engine.notify_urgent`** - High-priority unread notifications

4. **`engine.notify_blocked`** - Blocked notifications (audit)

### ENUM Type

**`engine.notify_urgency_enum`** - ROUTINE, IMPORTANT, URGENT, CRITICAL

## Dependencies

- `queue` -- Thread-safe UserNotificationQueue
- `threading` -- Thread safety for rate limiting and blocking checks
- `datetime` -- Timestamps
- `dataclasses` -- Notification and related dataclasses
- `enum` -- NotificationUrgency enum
- `string.Template` or similar -- Safe template rendering
- `bbsengine6.database` -- Database operations and user lookup
- (Optional) `bbsengine6.io` -- For UI display integration

## Known Limitations / TODOs

1. **No real-time push:** Notifications are queued locally; no websocket/network push (designed for single BBS instance).
2. **No notification expiration:** Notifications stored permanently in DB. May need cleanup/archival for long-lived systems.
3. **Template rendering:** Limited to simple `{var}` substitution. No conditional logic or loops.
4. **Group inheritance:** Groups are flat; no nested groups or role-based expansion.
5. **Moniker case sensitivity:** Monikers are case-sensitive. Should validate consistently across system.

## Known Issues

None currently. System is designed from scratch with security and simplicity in mind.

## Performance Characteristics

- **Notification send:** O(n) where n = number of recipients (database insert + queue push per recipient)
- **Notification retrieval:** O(1) queue.get() for live, O(log n) database query for historical
- **Rate limiting:** O(1) in-memory check with DB sync
- **Blocking check:** O(1) database lookup with index on (blocker, sender)
- **Group expansion:** O(m) where m = group size (one-time expansion at send time)
- **@everyone magic:** O(k) where k = number of active sessions (one-time expansion at send time)

## Backward Compatibility

This is a new module with no existing code dependencies. No breaking changes to existing APIs.

## Database Partitioning Strategy

For deployments with millions of notifications, partition `engine.__notify` and `engine.__notify_recipient` by date:

```sql
ALTER TABLE engine.__notify PARTITION BY RANGE (DATE_TRUNC('month', datecreated));
ALTER TABLE engine.__notify_recipient PARTITION BY RANGE (DATE_TRUNC('month', 
    (SELECT datecreated FROM engine.__notify WHERE id = notify_id)
));
```

See `/handbook/specs/database.md` for partition management procedures.

## Website Integration

The notification system is designed for website access:

**Query unread notifications for user:**
```sql
SELECT * FROM engine.notify_unread 
WHERE recipient_moniker = 'jam'
ORDER BY datecreated DESC;
```

**Check rate limit capacity:**
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

**Get blocked users:**
```sql
SELECT sender_moniker 
FROM engine.__notify_block 
WHERE blocker_moniker = 'jam';
```

**Mark notification as read from website:**
```sql
UPDATE engine.__notify_recipient 
SET dateread = now() 
WHERE notify_id = $1 AND recipient_moniker = $2;
```
