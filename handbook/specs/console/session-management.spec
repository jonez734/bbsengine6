# Session Management Module

## Overview

`session.py` displays and monitors active user sessions in real-time. Provides visibility into who is connected, when they logged in, and session activity.

**File:** `bbsengine6/console/session.py`  
**Size:** 85 lines  

---

## Standard Module Interface

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

All functions follow standard console module interface.

---

## Session Display

### main()

```python
def main(args, **kwargs) -> bool
```

Interactive session display. Queries and displays all active sessions.

**Behavior:**
1. Queries `engine.session` table for all active sessions
2. For each session, displays:
   - Member moniker
   - Session creation date/time
   - Session expiry time (and time remaining)
   - Last activity timestamp
   - User agent string
3. Displays session count summary
4. Refreshes periodically or on user command
5. Returns to menu on user exit

**Display Format:**
```
Active Sessions
===============

Moniker    | Created             | Expires             | Last Activity
-----------|---------------------|---------------------|-------------------
alice      | 2024-03-15 10:30:00 | 2024-03-15 12:30:00 | 2024-03-15 11:15:32
bob        | 2024-03-15 09:45:00 | 2024-03-15 11:45:00 | 2024-03-15 10:42:19
charlie    | 2024-03-15 08:00:00 | 2024-03-15 10:00:00 | 2024-03-15 09:58:47

Total Sessions: 3
```

---

## Database Query

### Session Table

```sql
SELECT * FROM engine.session
WHERE expires > NOW()
ORDER BY created DESC
```

**Columns Used:**
- `sessionid` — Unique session identifier
- `moniker` — Member who owns session (FK to engine.member)
- `created` — When session was established
- `expires` — When session will expire
- `lastactivity` — When session last had activity

### Result Processing

```python
with database.cursor(conn) as cur:
    cur.execute("SELECT * FROM engine.session WHERE ...")
    for row in database.resultiter(cur):
        # row is dict-like with column names as keys
        display_session(row)
```

**Row Structure:**
```python
{
    'sessionid': 'uuid-string',
    'moniker': 'alice',
    'created': datetime,
    'expires': datetime,
    'lastactivity': datetime,
    'useragent': 'Mozilla/5.0...'
}
```

---

## Session Lifecycle

### Session Creation

When member logs in:
```
engine.session INSERT:
  sessionid: UUID
  moniker: member_moniker
  created: NOW()
  expires: NOW() + session_timeout
  lastactivity: NOW()
```

### Session Activity Update

On each request:
```
engine.session UPDATE:
  lastactivity: NOW()
  [expires may be extended]
```

### Session Expiry

When `expires < NOW()`:
- Session is inactive/expired
- Not displayed in session list
- Can be cleaned up by background job

---

## Time Calculations

### Time Remaining

```python
expires = row['expires']  # datetime
now = datetime.now()
remaining = expires - now  # timedelta

if remaining > timedelta(0):
    display_remaining(remaining)
else:
    display "EXPIRED"
```

**Display Format:**
- `1h 23m 45s remaining`
- Or `EXPIRED` if past expiry

### Last Activity

```python
lastactivity = row['lastactivity']  # datetime
now = datetime.now()
ago = now - lastactivity

if ago < timedelta(seconds=60):
    display "Just now"
elif ago < timedelta(hours=1):
    display f"{ago.seconds // 60}m ago"
else:
    display f"{ago.seconds // 3600}h ago"
```

---

## User Interactions

### Menu Options

Typical session display menu (implementation may vary):
- [R]efresh — Refresh session list
- [K]ill — Kill specific session (if permitted)
- [X]it — Return to main menu

### Session Killing (if implemented)

```python
def kill_session(sessionid):
    # DELETE FROM engine.session WHERE sessionid = %s
    # OR UPDATE engine.session SET expires = NOW() WHERE sessionid = %s
```

**Requires:** Sysop access (via `access()` function)

---

## Error Handling

**Database Errors:**
- Connection fails → display error, return to menu
- Query fails → display error, return to menu
- No sessions → display "No active sessions"

**Display Errors:**
- Timezone conversion fails → display UTC time with note
- NULL lastactivity → display "Never" or "-"

---

## Dependencies

**Internal:**
- `bbsengine6.database` — Database connection, cursor, resultiter
- `bbsengine6.member` — Member lookup (if needed)
- `bbsengine6.io` — Input/output and formatting
- `bbsengine6.util` — Utility functions

**External:**
- `datetime` — Time calculations and formatting
- `psycopg` — PostgreSQL operations

---

## Related Operations

### Update Last Activity (from elsewhere)

```python
# In other modules, when session activity occurs:
database.update(
    table="engine.session",
    pk="sessionid",
    items={'lastactivity': func.now()},
    conn=conn
)
```

### Session Timeout Check

Background job (not in console):
```python
# SELECT COUNT(*) FROM engine.session WHERE expires < NOW()
# DELETE FROM engine.session WHERE expires < NOW()
```

---

## Future Enhancements

**Current Limitations:**
- Read-only display (no session killing implemented yet)
- No filtering by member
- No sorting options
- No session search

**Potential Features:**
- Kill session (with sysop permission)
- Filter by member moniker
- Search sessions
- Session statistics (total logins today, etc.)
- Activity graph/timeline
- Force logout for specific member

