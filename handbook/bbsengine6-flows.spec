# BBSEngine v6.0 Data Flow Specifications

**Version:** 6.0  
**Last Updated:** 2026-02-23

This document describes how data flows through BBSEngine v6.0 during critical operations, both at high level and in detailed sequence form.

## Table of Contents

1. [High-Level Workflows](#high-level-workflows)
2. [Detailed Sequence Flows](#detailed-sequence-flows)
3. [State Transformations](#state-transformations)
4. [Data Structures at Each Layer](#data-structures-at-each-layer)

---

## High-Level Workflows

### Workflow 1: User Login Flow

**Initiator:** User interacts with login prompt

**Steps:**
1. Terminal I/O displays login menu
2. User selects "Login" option
3. Module system loads login module
4. Login module prompts for credentials
5. Member module authenticates against database
6. Session module creates new session if valid
7. System returns success/failure message

**Outcome:** User logged in with active session, or error message displayed

**Time Complexity:** O(1) - single user lookup, single session creation

**Affected Systems:**
- Terminal I/O (io/getch, io/echo)
- Module system (module.py)
- Member module (member.py)
- Session module (session.py)
- Database layer (database.py)
- PostgreSQL (member, __session tables)

---

### Workflow 2: Message Posting Flow

**Initiator:** User selects message/post feature

**Steps:**
1. Terminal displays message menu
2. User selects "Post Message"
3. Module loads message composition module
4. Module displays form for:
   - Recipient/folder selection
   - Subject input
   - Message body (possibly using editor)
5. User submits message
6. Validation checks message content
7. Blurb module inserts message into database
8. Folder module updates folder metadata
9. System returns confirmation

**Outcome:** Message stored in database, confirmation displayed

**Time Complexity:** O(n) where n = message size

**Affected Systems:**
- Terminal I/O (menu, form, editor, listbox)
- Module system (module.py)
- Blurb module (blurb.py)
- Folder module (folder.py)
- Validation (util.py)
- Database layer (database.py)
- PostgreSQL (__blurb, __folder tables)

---

### Workflow 3: Navigation/Menu Flow

**Initiator:** User at main menu

**Steps:**
1. Terminal displays main menu with options
2. Menu widget shows available items (based on user flags)
3. User presses arrow keys to navigate
4. Menu highlights selected item
5. User presses ENTER to select
6. Menu resolves "requires" condition for item
7. Menu calls associated module or function
8. Result returned to menu
9. Menu redisplays or exits

**Outcome:** Selected action executed or submenu displayed

**Time Complexity:** O(1) per navigation step

**Affected Systems:**
- Terminal I/O (menu.py, io/getch, io/echo, io/screen)
- Member module (flags for visibility)
- Module system (module loading)
- Database (access control checks)

---

### Workflow 4: Module Execution Flow

**Initiator:** Menu, command-line, or programmatic call

**Steps:**
1. Caller invokes `module.run(args, modulename, **kwargs)`
2. Module system checks access permissions via `module.check()`
3. Module is loaded from filesystem via `module.load()`
4. Functions are validated via `validate_function()`
5. Module's `init()` called once per session
6. Module's `access()` checks user permission
7. Module's `buildargs()` parses and validates arguments
8. Module's `main()` executes module logic
9. Result caught and returned via `runcallback()`
10. Result returned to caller

**Outcome:** Module action completed, result returned or error displayed

**Time Complexity:** O(n) where n = module code execution time

**Affected Systems:**
- Module system (module.py)
- Database (access control)
- I/O (error display)
- All loaded modules

---

### Workflow 5: Web Request Flow

**Initiator:** HTTP request from browser

**Steps:**
1. Browser sends HTTP request to Apache
2. Apache routes to PHP endpoint
3. PHP bootstrap loads configuration
4. PHP calls `engine.php:displaypage()`
5. `displaypage()` loads Smarty template
6. Smarty template requests data (if needed)
7. PHP queries database or calls Python backend
8. Smarty renders template with data
9. JavaScript files injected into HTML
10. HTML sent back to browser
11. Browser renders page and executes JavaScript
12. User interacts with page

**Outcome:** HTML page rendered, JavaScript active for interactions

**Time Complexity:** O(database queries)

**Affected Systems:**
- Apache web server
- PHP engine (engine.php)
- Database (database.php queries)
- Smarty templating
- JavaScript execution
- Browser DOM

---

## Detailed Sequence Flows

### Sequence 1: User Login (Terminal)

```
USER                           TERMINAL I/O              BUSINESS LOGIC           DATABASE
 │                                 │                          │                     │
 │ Sees "Login" menu option        │                          │                     │
 │<────────────────────────────────│                          │                     │
 │                                 │                          │                     │
 │ Presses ENTER                   │                          │                     │
 ├─────────────────────────────────>                          │                     │
 │                                 │                          │                     │
 │                           menu.run()                        │                     │
 │                                 ├─ check access on "login" │                     │
 │                                 │   module                  │                     │
 │                                 ├────────────────────────────>                    │
 │                                 │         Query: has access to module?             │
 │                                 │<─────────────────────────    query                │
 │                                 │                              →│
 │                                 │                          Result: Yes│
 │                                 │<─────────────────────────────────│
 │                                 │                          │                     │
 │                          module.run()                      │                     │
 │                                 ├─ load login module        │                     │
 │                                 ├─ validate functions       │                     │
 │                                 ├─ init()                   │                     │
 │                                 │                          │                     │
 │ "Enter login ID:"               │                          │                     │
 │<────────────────────────────────│                          │                     │
 │ john.doe                        │                          │                     │
 ├─────────────────────────────────>                          │                     │
 │                                 │                          │                     │
 │ "Enter password:"               │                          │                     │
 │<────────────────────────────────│                          │                     │
 │ ••••••                          │                          │                     │
 ├─────────────────────────────────>                          │                     │
 │                                 │                          │                     │
 │                           buildargs()                      │                     │
 │                                 ├─ Parse login ID & password
 │                                 │                          │                     │
 │                           access()                         │                     │
 │                                 ├─ Check user has login permission│              │
 │                                 │                          │                     │
 │                           main(args)                       │                     │
 │                                 │  member.authenticate()    │                     │
 │                                 │├────────────────────────────>                   │
 │                                 │         Query: SELECT * FROM members          │
 │                                 │         WHERE loginid = 'john.doe'              │
 │                                 │                              →│
 │                                 │           Result: member record with hashed│
 │                                 │           password                     │
 │                                 │<─────────────────────────────────────│
 │                                 │  ├─ Compare provided password        │
 │                                 │     with stored hash                 │
 │                                 │  ├─ Hash matches!                    │
 │                                 │                          │                     │
 │                                 │  session.start()         │                     │
 │                                 │├────────────────────────────>                   │
 │                                 │         Query: INSERT INTO __session   │
 │                                 │         (id, expiry, lastactivity, │
 │                                 │          ipaddress, useragent, ...)    │
 │                                 │                              →│
 │                                 │           Result: Session ID (UUID)     │
 │                                 │<─────────────────────────────────────│
 │                                 │                          │                     │
 │                                 │  ├─ Store currentsessionid = UUID  │
 │                                 │  ├─ Return success                   │
 │                                 │                          │                     │
 │ "Welcome, john.doe!"            │                          │                     │
 │<────────────────────────────────│                          │                     │
 │                                 │                          │                     │
 │ [Display main menu]             │                          │                     │
 │<────────────────────────────────│                          │                     │
```

**State After Login:**
- `session.currentsessionid` = UUID
- `member.currentmoniker` = "john.doe"
- PostgreSQL `__session` table: new row inserted
- PostgreSQL `engine.member` table: `lastlogin` updated

---

### Sequence 2: Message Posting (Terminal)

```
USER                       TERMINAL I/O         BUSINESS LOGIC         DATABASE/EDITOR
 │                             │                     │                      │
 │ "Post Message" selected     │                     │                      │
 │─────────────────────────────>                     │                      │
 │                             │                     │                      │
 │                        module.run(posteditor)     │                      │
 │                             ├─ load posteditor    │                      │
 │                             │                     │                      │
 │ "Select recipient:"         │                     │                      │
 │<────────────────────────────│                     │                      │
 │                             │                listbox.run()               │
 │                             │                     ├─ fetchpage(1)       │
 │                             │                     │    Query: SELECT *   │
 │                             │                     │    FROM __member     │
 │                             │                     │    LIMIT 20          │
 │                             │                     │                    ↓│
 │ [Listbox of members] 1/5    │                     │         [Database query]
 │  ☐ alice                   │                     │                    ↓│
 │  ☐ bob                     │                     │         Result: list[dict]
 │  ☐ carol                   │                     │                      │
 │<────────────────────────────│                     │<─────────────────────│
 │                             │                     │                      │
 │ [UP/DOWN arrows] → carol    │                     │                      │
 ├─────────────────────────────>                     │                      │
 │                             │                listbox.handle()           │
 │ [ENTER]                     │                     │                      │
 ├─────────────────────────────>                     │                      │
 │                             │                listbox.run() returns      │
 │                             │                ListboxResult(item=carol)  │
 │                             │                     │                      │
 │ "Enter subject:"            │                     │                      │
 │<────────────────────────────│                     │                      │
 │ Re: Project Status          │                     │                      │
 ├─────────────────────────────>                     │                      │
 │                             │                     │                      │
 │ "Enter message (. to end):" │                     │                      │
 │<────────────────────────────│                     │                      │
 │ I'm working on the new      │                     │                      │
 │ feature. Should be ready    │                     │                      │
 │ next week.                  │                     │                      │
 │ .                           │                     │                      │
 ├─────────────────────────────>                     │                      │
 │                             │                     │                      │
 │                             │             blurb.insert()                 │
 │                             │                     ├─ Build record with   │
 │                             │                        to, from, subject,
 │                             │                        body, datecreated    │
 │                             │                     ├─ INSERT INTO         │
 │                             │                        __blurb              │
 │                             │                     │                    ↓│
 │                             │                     │   INSERT INTO __blurb
 │                             │                     │   (folderid, to_id,   │
 │                             │                     │    from_id, subject,  │
 │                             │                     │    body,              │
 │                             │                     │    datecreated)       │
 │                             │                     │     VALUES (...)      │
 │                             │                     │                    ↓│
 │                             │                     │      COMMIT           │
 │                             │                     │                    ↓│
 │                             │                     │  Result: message ID   │
 │                             │                     │         12345         │
 │                             │<────────────────────────────────────────────│
 │                             │                     │                      │
 │ "Message posted! (ID:12345)"│                     │                      │
 │<────────────────────────────│                     │                      │
 │                             │                     │                      │
```

**State After Posting:**
- PostgreSQL `__blurb` table: new row inserted with ID 12345
- PostgreSQL `__folder` table: message count incremented
- User sees confirmation with message ID

---

### Sequence 3: Module Execution Flow

```
CALLER                   MODULE SYSTEM          DATABASE/FILESYSTEM   RESULT
  │                          │                         │                  │
  │ module.run(args,        │                         │                  │
  │            "messages")  │                         │                  │
  ├──────────────────────────>                         │                  │
  │                          │                         │                  │
  │                   module.check()                   │                  │
  │                          ├─ Query: Is "messages"   │                  │
  │                          │  module allowed for     │                  │
  │                          │  current user?          │                  │
  │                          │──────────────────────────>                  │
  │                          │     SELECT * FROM       │                  │
  │                          │     __member_flags      │                  │
  │                          │     WHERE user_id = ? AND                  │
  │                          │     module = "messages" │                  │
  │                          │<──────────────────────────                  │
  │                          │  ├─ Result: access=True │                  │
  │                          │                         │                  │
  │                   module.load()                    │                  │
  │                          ├─ Find: bbsengine6/      │                  │
  │                          │  modules/messages/      │                  │
  │                          │  __init__.py            │                  │
  │                          │──────────────────────────>                  │
  │                          │  ├─ Load module from    │                  │
  │                          │     filesystem          │                  │
  │                          │<──────────────────────────                  │
  │                          │                         │                  │
  │                   validate_function                │                  │
  │                          ├─ Check init()           │                  │
  │                          ├─ Check access()         │                  │
  │                          ├─ Check buildargs()      │                  │
  │                          ├─ Check main()           │                  │
  │                          │  ├─ All signatures valid
  │                          │                         │                  │
  │                   messages.init()                  │                  │
  │                          ├─ One-time setup         │                  │
  │                          │                         │                  │
  │                   messages.access()                │                  │
  │                          ├─ Check runtime access   │                  │
  │                          │  ├─ Result: True        │                  │
  │                          │                         │                  │
  │                   messages.buildargs()             │                  │
  │                          ├─ Parse args, build      │                  │
  │                          │  argparse.Namespace     │                  │
  │                          │  ├─ Result: args obj    │                  │
  │                          │                         │                  │
  │                   runcallback(main)                │                  │
  │                          ├─ Try:                   │                  │
  │                          │   messages.main(args)   │                  │
  │                          │   ├─ [execute module]   │                  │
  │                          │   └─ Result: message    │                  │
  │                          │      list               │                  │
  │                          │ Except Exception:       │                  │
  │                          │   ├─ io.echo(error)     │                  │
  │                          │   └─ Result: None/error │                  │
  │                          │                         │                  │
  │<──────────────────────────                         │        Result: [ │
  │  Result returned                                                { id: 1, from: 'alice', ...│
  │                                                       { id: 2, from: 'bob', ...│
  │                                                     ]
```

**Key Points:**
1. Access checked before loading
2. Module functions validated
3. Execution wrapped in try/except
4. Errors display gracefully
5. Result returned to caller

---

## State Transformations

### State 1: Before Login

```
Session State:
  currentsessionid = None
  lastactivity = None

Member State:
  currentmoniker = None
  currentid = None
  currentflags = {}

Database State:
  __session: empty or expired rows only
  engine.member: lastlogin not updated
```

### State 2: During/After Login

```
Session State:
  currentsessionid = "550e8400-e29b-41d4-a716-446655440000"
  lastactivity = "2026-02-23T18:40:00"

Member State:
  currentmoniker = "john.doe"
  currentid = 123
  currentflags = {"admin": False, "moderator": False}

Database State:
  __session: new row with session UUID
  engine.member: lastlogin = now()

User Can:
  - Access all modules allowed by flags
  - Create/read/update messages
  - Edit profile
  - Access restricted features
```

### State 3: During Message Posting

```
Session State:
  [unchanged, continues active]

Module State:
  current_module = "posteditor"
  editor_mode = "composing"

Database State:
  [no changes yet, in transaction]
  
User Input:
  to = "carol"
  subject = "Re: Project Status"
  body = "..."
```

### State 4: After Message Posting

```
Database State:
  __blurb: new row inserted
    {
      id: 12345,
      folderid: 5,
      to_id: 3,
      from_id: 123,
      subject: "Re: Project Status",
      body: "...",
      datecreated: "2026-02-23T18:45:00"
    }
  __folder: message_count incremented
    message_count: 156 → 157

Module State:
  current_module = "main_menu"
  editor_mode = None

Message Queue (if async):
  ├─ Notify "carol" of new message
  └─ Update folder statistics
```

---

## Data Structures at Each Layer

### Data Layer (PostgreSQL)

**Session Record:**
```sql
CREATE TABLE engine.__session (
  id UUID PRIMARY KEY,
  expiry TIMESTAMP NOT NULL,
  lastactivity TIMESTAMP,
  data JSONB,
  ipaddress INET,
  useragent TEXT,
  datecreated TIMESTAMP DEFAULT NOW(),
  dateupdated TIMESTAMP DEFAULT NOW(),
  moniker VARCHAR(32)
);
```

**Member Record:**
```sql
CREATE TABLE engine.member (
  id SERIAL PRIMARY KEY,
  loginid VARCHAR(32) UNIQUE,
  moniker VARCHAR(32),
  email VARCHAR(254),
  password VARCHAR(255),  -- bcrypt hash
  credits INT DEFAULT 100,
  flags JSONB DEFAULT '{}',
  attrs JSONB DEFAULT '{}',
  ui TEXT[],  -- ARRAY of interface types
  datecreated TIMESTAMP DEFAULT NOW(),
  dateupdated TIMESTAMP,
  lastlogin TIMESTAMP
);
```

**Message Record:**
```sql
CREATE TABLE engine.__blurb (
  id SERIAL PRIMARY KEY,
  folderid INT NOT NULL REFERENCES __folder(id),
  to_id INT REFERENCES engine.member(id),
  from_id INT REFERENCES engine.member(id),
  subject TEXT,
  body TEXT,
  attributes JSONB DEFAULT '{}',
  datecreated TIMESTAMP DEFAULT NOW()
);
```

### Business Logic Layer (Python Dicts)

**Session Object:**
```python
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "expiry": "2026-02-24T10:30:00",
  "lastactivity": "2026-02-23T18:40:00",
  "data": {
    "preferences": {
      "colormode": "ansi",
      "width": 80
    }
  },
  "ipaddress": "192.168.1.1",
  "useragent": "Terminal v1.0",
  "datecreated": "2026-02-23T09:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "moniker": "john.doe"
}
```

**Member Object:**
```python
{
  "id": 123,
  "loginid": "john.doe",
  "moniker": "john.doe",
  "email": "john@example.com",
  "password": "$2b$12$...",  # bcrypt hash
  "credits": 500,
  "flags": {
    "admin": False,
    "moderator": False,
    "verified": True
  },
  "attrs": {
    "signature": "John Doe",
    "bio": "Software developer"
  },
  "ui": ["term", "web"],
  "datecreated": "2026-01-01T00:00:00",
  "dateupdated": "2026-02-23T18:40:00",
  "lastlogin": "2026-02-23T18:40:00"
}
```

**Message Object:**
```python
{
  "id": 12345,
  "folderid": 5,
  "to_id": 3,
  "from_id": 123,
  "to_moniker": "carol",
  "from_moniker": "john.doe",
  "subject": "Re: Project Status",
  "body": "I'm working on the new feature...",
  "attributes": {
    "read": False,
    "replied": False,
    "flagged": False
  },
  "datecreated": "2026-02-23T18:45:00"
}
```

### Presentation Layer (Terminal)

**Menu Display:**
```
╔══════════════════════════════════════╗
║          BBSENGINE MAIN MENU         ║
╠══════════════════════════════════════╣
║ ☐ Read Messages                      ║
║ ☒ Post Message                       ║
║ ☐ Edit Profile                       ║
║ ☐ Check Mail                         ║
║ ☐ Logout                             ║
╠══════════════════════════════════════╣
║ [ENTER] Select  [ESC] Quit  [?] Help ║
╚══════════════════════════════════════╝
```

**Listbox Display:**
```
Message List (Page 1 of 5)
 1. alice - Need feedback on design    | 2026-02-23 10:15
 2. bob - Project status update        | 2026-02-23 14:22
 3. carol - Upcoming meeting           | 2026-02-23 15:30
 4. dave - Code review requested       | 2026-02-23 16:45

[UP/DOWN] Navigate  [PAGEUP/DOWN] Page  [ENTER] Select  [ESC] Exit
```

### Presentation Layer (Web/PHP)

**JSON Response:**
```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "id": 456,
        "from": "alice",
        "subject": "Feedback Request",
        "date": "2026-02-23T10:15:00",
        "read": false
      },
      {
        "id": 457,
        "from": "bob",
        "subject": "Status Update",
        "date": "2026-02-23T14:22:00",
        "read": true
      }
    ]
  },
  "timestamp": "2026-02-23T18:50:00"
}
```

---

## Cross-Layer Data Transformation

### Example: Message from Database to Terminal Display

**Step 1: Database Query**
```sql
SELECT * FROM engine.__blurb
WHERE id = 12345
```

**Result (Raw):**
```
id    | folderid | to_id | from_id | subject      | body        | datecreated
------|----------|-------|---------|--------------|-------------|--------------------
12345 | 5        | 3     | 123     | Project...   | I'm...      | 2026-02-23 18:45:00
```

**Step 2: Business Logic Layer (Python dict)**
```python
{
  "id": 12345,
  "folderid": 5,
  "to_id": 3,
  "from_id": 123,
  "to_moniker": "carol",     # Fetched in separate query
  "from_moniker": "john.doe",
  "subject": "Project Status Update",
  "body": "I'm working on the new feature...",
  "datecreated": "2026-02-23T18:45:00"
}
```

**Step 3: Presentation Layer (Terminal)**
```
From: john.doe
To:   carol
Date: 2026-02-23 18:45 (Tue)
Subj: Project Status Update
───────────────────────────────────────

I'm working on the new feature. Should be
ready next week.

───────────────────────────────────────
[R]eply  [F]orward  [D]elete  [ESC] Back
```

---

## Performance Considerations

### Query Optimization

**High-Frequency Queries:**
1. `member` lookup by loginid - **Indexed** on loginid
2. `__session` lookup by id - **Indexed** on id (PRIMARY KEY)
3. `__blurb` lookup by folderid - **Indexed** on folderid
4. Member flags retrieval - **Cached** in memory

**Pagination:**
- Listbox uses LIMIT/OFFSET for large datasets
- Default page size: 20 items
- Maintains current_page to avoid re-fetching

### Connection Pooling

- Min pool size: 1 connection
- Max pool size: 20 connections
- Timeout: 30 seconds
- Reuses connections across requests

### Caching Strategy

- Member flags cached during session
- OID lookups cached in memory
- SQL templates cached after first compilation

---

## Error Handling Flows

### Database Error Flow

```
SQL Query Execution
  │
  ├─ psycopg.Error
  │  ├─ Log via util.logentry()
  │  ├─ io.echo(error message, level="error")
  │  └─ Return None/False/[]
  │
  └─ Connection Timeout
     ├─ Reconnect via pool
     └─ Retry query (1x)
```

### Module Execution Error Flow

```
module.run(modulename)
  │
  ├─ module.check() fails
  │  └─ io.echo("Access denied")
  │
  ├─ module.load() fails
  │  └─ io.echo("Module not found")
  │
  ├─ validate_function() fails
  │  └─ io.echo("Invalid module API")
  │
  ├─ module.main() raises Exception
  │  ├─ runcallback() catches
  │  ├─ io.echo_traceback(exception)
  │  └─ Return None/error status
  │
  └─ Return result to caller
```

---

*Data Flow Specification for BBSEngine v6.0*
