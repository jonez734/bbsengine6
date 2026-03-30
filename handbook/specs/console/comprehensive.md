# Console Module Comprehensive Specification

This is the consolidated detailed reference for the bbsengine6 console module. For quick navigation, see the index at `console.md`.

---

# Part 1: Overview & Architecture

## Module Overview

The console module (`bbsengine6/console/`) provides the administrative command-line interface for BBS Engine 6. It handles:

- **Database initialization** via two-stage setup
- **Member management** with interactive CRUD operations
- **Member approval workflow** for new account processing
- **Session monitoring** for active user tracking
- **System configuration** for email and notifications (incomplete)
- **Plugin architecture** for extensible console commands

**Statistics:**
- Total: ~2,203 lines across 21 Python modules
- Entry points: `__main__.py`, `main.py`
- Subcommands: member, session, memberapproval, email, notify
- Database checks: 11 verification modules

## File Structure

```
bbsengine6/console/
├── Core Framework
│  ├── __init__.py (1)                    Module init
│  ├── __main__.py (49)                   CLI entry point
│  ├── lib.py (311)                       Module discovery & framework
│  └── main.py (199)                      Database stages & interactive menu
│
├── User Management
│  ├── member.py (610)                    Member CRUD & editing
│  ├── memberapproval.py (128)            Approval workflow
│  └── notify.py (25)                     Notifications (stub)
│
├── Database Verification (11 files, 1,074 lines)
│  ├── Role Management
│  │  ├── checkroles.py (43)
│  │  └── checkwebserverrole.py (48)
│  ├── Extensions & Schema
│  │  ├── checkextensions.py (46)
│  │  └── checkschema.py (39)
│  ├── Database & User
│  │  ├── checkdatabase.py (78)
│  │  ├── checksuperuser.py (55)
│  │  └── checkloginid.py (95)
│  ├── Functions & Procedures
│  │  └── checkfunctions.py (61)
│  └── Data Structures
│     ├── checkclasses.py (57)
│     ├── checkflag.py (74)
│     └── checknotify.py (83)
│
├── Session Management
│  ├── session.py (85)                    Session display
│  └── email.py (87)                      Email config (incomplete)
│
└── Utility
   └── createdatabase.py (29)             DB creation helper
```

---

## Architecture & Design Patterns

### Standard Module Interface

All console modules implement exactly four functions:

```python
def init(args, **kwargs) -> bool
    """Initialize module (called once at startup)."""

def access(args, op, **kwargs) -> bool
    """Check user access permissions."""

def buildargs(args, **kwargs) -> ArgumentParser | None
    """Build CLI argument parser."""

def main(args, **kwargs) -> bool
    """Execute module functionality."""
```

**Key Requirements:**
- All four functions must exist and be callable
- All must accept `**kwargs` for framework compatibility
- Module must have docstring (first line = help text)
- Access control: `access(op)` with operation type checking

### Module Discovery Pattern

Dynamic module discovery automatically finds valid console modules:

1. Scans `bbsengine6/console/` directory for `.py` files
2. Validates: has `main()` function + docstring
3. Caches results (cleared in debug mode)
4. Returns list of valid module names
5. **Benefit:** Add new module, it's auto-discovered

### Stage-Based Initialization

**Stage 0 (Prerequisites):**
1. Connect to PostgreSQL system database
2. Check/create roles (web, sysop, term)
3. Load core functions
4. Verify superuser permissions
5. Verify www-data role
6. Create main BBS database

**Stage 1 (Database Structure):**
1. Connect to main BBS database
2. Create/verify extensions (pgcrypto, ltree, citext)
3. Import/verify schema
4. Import/verify stored functions
5. Create/verify tables
6. Initialize system flags
7. Verify notification system

**Rationale:** Granular control, transaction isolation, prerequisite validation

### Transaction Management

All database operations follow strict control:

```python
with database.connect(args, pool=pool) as conn:
    with database.cursor(conn) as cur:
        # Execute operations
    conn.commit()  # or rollback on error
```

**Rules:**
- Always use context managers
- Commit/rollback explicitly (no auto-commit)
- Multiple transactions per operation
- Read-only queries don't require commit

### Interactive Menu Pattern

Consistent navigation model:
- Display status/data at top
- Show menu options with bracket notation: `[M]embers`, `[N]ew`, `[X]it`
- Prompt for user choice
- Execute selected action
- Return to menu (loop until exit)

### Deep Copy Comparison Pattern

Member editing tracks changes through deep copy:

```python
original = copy.deepcopy(member)
# User edits member object
# Display shows fields where original != member
# Only changed fields highlighted
```

### Connection Pool Passing

Database connections passed through `**kwargs`:

```python
pool = database.getpool(args)
lib.runmodule(args, "member", pool=pool)
```

---

## Execution Flow

### CLI Entry Point

```
zoidoffice [subcommand] [args]
  ├─ If subcommand provided:
  │   ├─ lib.discover_console_modules()
  │   ├─ lib.build_subcommand_parser()
  │   └─ lib.handle_subcommand(args, subcommand)
  │       └─ lib.runmodule(args, f"console.{subcommand}")
  │           ├─ init()
  │           ├─ buildargs()
  │           ├─ parse_args()
  │           └─ main()
  │
  └─ If no subcommand:
      └─ lib.runmodule(args, "console.main")
          └─ main.main(args)
              ├─ main.stage_zero() [DB setup]
              ├─ main.stage_one()  [DB init]
              └─ Interactive loop
```

### Stage Zero Sequence

```
1. Connect to 'postgres' database
2. lib.checkroles()          → Verify/create roles
3. lib.checkfunctions(0)     → Load core functions
4. lib.checksuperuser()      → Verify permissions
5. lib.checkwebserverrole()  → Verify www-data
6. lib.createdatabase()      → Create BBS database
```

### Stage One Sequence

```
1. Connect to BBS database
2. lib.checkextensions()     → Create extensions
3. lib.checkschema()         → Create schema
4. lib.checkfunctions(1)     → Load engine functions
5. lib.checkclasses()        → Create tables
6. lib.checkflag()           → Create flag tables
7. lib.checknotify()         → Create notification system
```

### Interactive Menu Loop

```
main.main()
  ├─ Display member count & DB info
  ├─ Show menu: [M]embers [S]essions [X]it
  │
  ├─ [M] → member.main()
  │   ├─ Menu: [N]ew [E]dit [A]pprovals [Q]uit
  │   ├─ [N] → member.add()
  │   ├─ [E] → member.edit()
  │   ├─ [A] → memberapproval.main()
  │   └─ [Q] → Return to main
  │
  ├─ [S] → session.main()
  │   └─ Display active sessions
  │
  └─ [X] → Exit
```

---

# Part 2: Core Components

## lib.py: Module Discovery & Framework

### discover_console_modules()

```python
def discover_console_modules(args, force_refresh=False) -> list
```

Auto-discovers valid console modules.

**Behavior:**
1. Scans package for `.py` files
2. Validates each via `validate_module_for_discovery()`
3. Returns list of module names
4. Caches results (clears in debug mode)

**Returns:** `["member", "session", "memberapproval", ...]`

### validate_module_for_discovery()

```python
def validate_module_for_discovery(module_fullname) -> bool
```

Validates module requirements:
- Can be imported
- Has `main()` function
- Has docstring

### build_subcommand_parser()

```python
def build_subcommand_parser(parser, **kwargs) -> None
```

Adds discovered modules as subcommands to ArgumentParser.

### handle_subcommand()

```python
def handle_subcommand(args, subcommand, **kwargs) -> bool
```

Routes to specific subcommand module and executes it.

### runmodule()

```python
def runmodule(args, submodule, **kwargs) -> Any
```

Generic module execution wrapper. Imports module, calls init/buildargs/main.

### Wrapper Functions

Each check module has wrapper in lib.py:

```python
def checkroles()
def checkextensions()
def checkdatabase()
# ... etc for all check modules
```

---

## main.py: Initialization & Interactive Console

### init()

Initialize module (returns True).

### access()

Check access (stub, returns True).

### buildargs()

Return None (no CLI args).

### stage_zero()

```python
def stage_zero(args, **kwargs) -> bool
```

Database setup prerequisites. Returns True if all checks pass, False on first failure.

**Steps:**
1. Connect to `postgres` database
2. `lib.checkroles()` — Verify/create roles
3. `lib.checkfunctions(stage=0)` — Load core functions
4. `lib.checksuperuser()` — Verify permissions
5. `lib.checkwebserverrole()` — Verify www-data
6. `lib.createdatabase()` — Create main database

### stage_one()

```python
def stage_one(args, **kwargs) -> bool
```

Database structure initialization. Returns True if all checks pass, False on first failure.

**Steps:**
1. Connect to BBS database
2. `lib.checkextensions()` — Create extensions
3. `lib.checkschema()` — Create schema
4. `lib.checkfunctions(stage=1)` — Load engine functions
5. `lib.checkclasses()` — Create tables
6. `lib.checkflag()` — Create flag tables
7. `lib.checknotify()` — Create notification system

### main()

```python
def main(args, **kwargs) -> bool
```

After successful initialization, displays interactive menu.

**Display:**
```
BBS Engine 6 Console
Database: bbsengine6
Members: 42
[M]embers  [S]essions  [X]it
```

**Menu Options:**
- [M] → `member.main(args, pool=pool)`
- [S] → `session.main(args, pool=pool)`
- [X] → Exit

---

## member.py: Member Management

### add()

```python
def add(args, **kwargs) -> bool
```

Interactive member creation.

**Workflow:**
1. Call `_edit(args, "add", {})`
2. Collect: moniker, loginid, email, password, credits, ui, sysop
3. Validate all fields
4. Create database records
5. Configure database role
6. Commit transaction

### edit()

```python
def edit(args, **kwargs) -> bool
```

Interactive member selection and editing.

1. Prompt for moniker to edit
2. Load member via `libmember.find()`
3. Call `_edit(args, "edit", member)`
4. Commit changes

### _edit()

```python
def _edit(args, mode, member, **kwargs) -> bool
```

Interactive editing interface (used for both add and edit).

**Behavior:**
1. Deep copy original member for comparison
2. For each field: prompt for input, validate, update
3. Display summary of changes
4. Prompt for confirmation
5. Return True if saved, False if cancelled

**Fields:**
- moniker, loginid, email, password, credits, ui, flags, sysop

### editflags()

```python
def editflags(args, moniker, **kwargs) -> bool
```

Interactive member flag editor. Toggle each system flag.

### editui()

```python
def editui(args, rolename) -> bool
```

Configure UI preference (web vs terminal).

### configurerole()

```python
def configurerole(args, rolename, sysop, **kwargs) -> bool
```

Create member database role with permissions.

**Steps:**
1. Check if role exists
2. Create if missing
3. Call `setui()` to configure interface permissions
4. Grant sysop permissions if requested

### setui()

```python
def setui(args, rolname, ui, **kwargs) -> bool
```

Grant or revoke web interface permissions.

---

## memberapproval.py: Approval Workflow

### access()

**Requires:** SYSOP flag on current user

```python
def access(args, op, **kwargs) -> bool:
    # Check member.checkflag("SYSOP")
    return True if sysop else False
```

### main()

```python
def main(args, **kwargs) -> bool
```

Interactive approval workflow.

**Sequence:**
1. Query: `SELECT * FROM engine.member WHERE approvedbyid IS NULL`
2. For each member:
   - Display info
   - Prompt: "Email verified? (Y/n)" → Set EMAILVERIFIED flag
   - Prompt: "Approve member? (Y/n)"
     - Yes: Set APPROVED flag, update approvedbyid/approveddate
     - No: Submenu [D]elete, [S]kip, [C]ancel
   - Commit transaction
3. Return True

---

## session.py: Session Management

### main()

```python
def main(args, **kwargs) -> bool
```

Display active user sessions.

**Behavior:**
1. Query: `SELECT * FROM engine.session WHERE expires > NOW()`
2. For each session:
   - Display: moniker, created, expires, lastactivity
   - Calculate remaining time
   - Calculate time since last activity
3. Show summary (total sessions)
4. Menu options: [R]efresh, [X]it

---

## Database Check Modules

### Pattern

All check modules follow same pattern:

```python
def init(), access(), buildargs(), main()

def main():
    # Check if component exists
    if exists:
        return True
    
    # Create if missing
    try:
        create()
        if exists:
            return True
    except Exception:
        log_error()
    
    return False
```

### Role Management

**checkroles.py (43 lines)**
- Verify/create roles: web, sysop, term
- SQL: `CREATE ROLE [name]`

**checkwebserverrole.py (48 lines)**
- Verify www-data role exists
- Required for web server database access

### Extensions & Schema

**checkextensions.py (46 lines)**
- Verify extensions: pgcrypto, ltree, citext
- SQL: `CREATE EXTENSION [name]`

**checkschema.py (39 lines)**
- Verify `engine` schema exists
- Import schema.sql if missing
- Creates tables, views, indexes

### Database & User

**checkdatabase.py (78 lines)**
- Verify/create main BBS database
- SQL: `CREATE DATABASE bbsengine6`

**checksuperuser.py (55 lines)**
- Verify current user permissions
- Requires: SUPERUSER or (CREATEDB + CREATEROLE + CANLOGIN)

**checkloginid.py (95 lines)**
- Verify system login ID via DBus
- Linux-specific integration

### Functions & Procedures

**checkfunctions.py (61 lines)**
- Two stages:
  - Stage 0: Core functions (before DB creation)
  - Stage 1: Engine functions (after DB created)
- Import from functions.sql

### Data Structures

**checkclasses.py (57 lines)**
- Verify table existence
- Create if missing

**checkflag.py (74 lines)**
- Verify flag tables
- Create junction table for member-to-flag mapping

**checknotify.py (83 lines)**
- Verify notification system schema
- Create types and tables

---

# Part 3: Workflows & Data

## Workflow: Add New Member

```
1. member.add(args)
   
2. member._edit(args, "add", {})
   └─ Display form
   └─ Collect: moniker, loginid, email, password, credits, ui, sysop
   └─ Validate all fields
   └─ Display summary
   └─ Confirm save? (Y/n)
   
3. Database operations (if confirmed)
   
   a. libmember.insert(moniker, loginid, email)
      └─ INSERT INTO engine.member
      └─ Returns member dict with memberid
   
   b. libmember.setpassword(moniker, password)
      └─ Hash password with bcrypt
      └─ UPDATE engine.member SET password = %s
   
   c. libmember.setcredits(moniker, credits)
      └─ UPDATE engine.member SET credits = %s
   
   d. For each flag:
      └─ libmember.setflag(moniker, flagid)
      └─ INSERT INTO engine.map_member_flag
   
   e. configurerole(args, moniker, sysop)
      ├─ Check role exists
      ├─ Create if missing: CREATE ROLE moniker
      ├─ setui(args, moniker, member['ui'])
      │  └─ GRANT ... or REVOKE ... on tables
      └─ If sysop: Grant sysop privileges
   
   f. conn.commit()
      └─ Transaction committed

4. Return True (success) or False (error/cancel)
```

## Workflow: Approve Pending Member

```
1. memberapproval.main(args)
   
2. Query pending members:
   └─ SELECT * FROM engine.member WHERE approvedbyid IS NULL
   
3. For each member:
   
   a. Display info (moniker, email, created date)
   
   b. Prompt: "Email verified? (Y/n)"
      └─ If yes: libmember.setflag(moniker, "EMAILVERIFIED", True)
   
   c. Prompt: "Approve member? (Y/n)"
      
      If yes:
      ├─ UPDATE engine.member
      │  SET approvedbyid = %s, approveddate = NOW()
      │  WHERE moniker = %s
      └─ libmember.setflag(moniker, "APPROVED", True)
      
      If no:
      ├─ Submenu: [D]elete, [S]kip, [C]ancel
      ├─ If Delete: DELETE FROM engine.member WHERE moniker = %s
      ├─ If Skip: Leave unapproved
      └─ If Cancel: Revert
   
   d. conn.commit()
      └─ Changes committed
   
   e. Continue to next member

4. Return True
```

## Workflow: View Active Sessions

```
1. session.main(args)
   
2. Query active sessions:
   └─ SELECT * FROM engine.session WHERE expires > NOW()
   
3. For each session row:
   
   a. Extract fields:
      ├─ moniker
      ├─ created (login time)
      ├─ expires (expiration time)
      ├─ lastactivity (last activity timestamp)
      └─ useragent
   
   b. Calculate remaining time:
      └─ remaining = expires - NOW()
      └─ Format: "1h 23m 45s" or "EXPIRED"
   
   c. Calculate last activity:
      └─ ago = NOW() - lastactivity
      └─ Format: "5m ago", "23h ago", "Just now"
   
   d. Display in table:
      moniker | created | expires | lastactivity
      --------|---------|---------|-------------
      alice   | 10:30   | 12:30   | 11:15 (45m ago)

4. Display summary: Total Sessions: N

5. Menu: [R]efresh, [X]it

6. Return True
```

---

## Data Structures

### Member Object

```python
{
    'memberid': 42,
    'moniker': 'alice',
    'loginid': 'alice_user',
    'email': 'alice@example.com',
    'password': '$2b$12$...',  # hashed
    'credits': 1000,
    'ui': 'web',  # or 'term'
    'sysop': True,  # or False
    'created': datetime,
    'lastlogin': datetime,
    'approvedbyid': 1,  # or None if pending
    'approveddate': datetime,
    # ... other fields
}
```

### Session Object

```python
{
    'sessionid': 'uuid-string-12345',
    'moniker': 'alice',
    'created': datetime(2024, 3, 15, 10, 30, 0),
    'expires': datetime(2024, 3, 15, 12, 30, 0),
    'lastactivity': datetime(2024, 3, 15, 11, 15, 32),
    'useragent': 'Mozilla/5.0...'
}
```

### Flag Object

```python
{
    'flagid': 'APPROVED',
    'description': 'Member account approved',
    'value': 1  # or 0
}
```

---

## Transaction Boundaries

### Member Add

```
BEGIN
  INSERT INTO engine.member (...)
  UPDATE engine.member SET password = ... WHERE moniker = ...
  INSERT INTO engine.map_member_flag (...)
  CREATE ROLE moniker ...
  GRANT ... ON SCHEMA engine TO moniker
COMMIT (or ROLLBACK on error)
```

### Member Approval

```
For each member:
  BEGIN
    UPDATE engine.member SET approvedbyid, approveddate WHERE moniker = ...
    INSERT INTO engine.map_member_flag (EMAILVERIFIED, APPROVED)
  COMMIT (or ROLLBACK on error)
```

### Database Setup

```
Each check module:
  BEGIN
    [Check/create operations]
  COMMIT (or ROLLBACK on error)
```

---

# Part 4: Dependencies & Error Handling

## Dependencies

### External Packages

- `psycopg` — PostgreSQL operations
- `dbus` — Linux DBus (checkloginid.py)
- `argparse` — CLI argument parsing
- `bcrypt` — Password hashing (via libmember)

### Internal (bbsengine6)

- `bbsengine6.database` — Connection pooling, CRUD
- `bbsengine6.member` — Member entity operations (libmember)
- `bbsengine6.io` — Input/output formatting
- `bbsengine6.util` — Utility functions
- `bbsengine6.session` — Session management
- `bbsengine6.module` — Module framework

### Standard Library

- `argparse` — Argument parsing
- `copy` — Deep copy for change tracking
- `datetime` — Timestamps
- `importlib` — Dynamic module loading
- `inspect` — Signature inspection
- `pkgutil` — Package scanning
- `sys` — System functions
- `typing` — Type hints

---

## Error Handling

### Database Errors

- Query fails → return False, log traceback
- Transaction fails → rollback, return False
- Connection fails → return False, log error
- Update fails → rollback, return False

### User Input Errors

- Invalid choice → prompt again
- Missing required field → highlight, prompt again
- Duplicate moniker → show error, prompt again
- Invalid email format → show error, prompt again

### Module Errors

- Module import fails → logged, skipped
- Module validation fails → not added to subcommand list
- Module function raises → caught, logged, traced

### Access Control

- Non-sysop attempts approval → access denied
- Unknown member → access denied

### Stop-on-Failure

- Stage 0/1 errors → entire stage fails
- User must fix issue and restart
- Individual module errors → caught and logged

---

## Error Recovery

### Failed Member Add

```
If validation error:
  └─ Form re-displayed, user can correct
  └─ No database changes

If database error:
  └─ Transaction rolled back automatically
  └─ Error shown to user
  └─ Form returned, user can retry or cancel
```

### Failed Approval

```
If database error:
  └─ Transaction rolled back
  └─ Error logged and displayed
  └─ User can retry same member or continue to next
```

### Failed Stage Setup

```
If stage_zero fails at step N:
  └─ Stop immediately
  └─ Log error with details
  └─ User must fix and restart

If stage_one fails at step N:
  └─ Database already exists
  └─ Can restart stage_one independently
```

---

## Incomplete Features

### notify.py (Status: Stub)

**Current:** Module structure exists, no implementation.

**Intended Design:**
- Display notifications
- Mark read/unread
- Manage preferences
- Clear old notifications

**Database Schema:** Defined in checknotify.py (engine.notification, engine.subscription)

### email.py (Status: Incomplete)

**Current:** Stub module structure.

**Intended Design:**
- SMTP configuration
- Email templates
- Email accounts
- Notification delivery
- Email logging

---

## Extension Points

Add new console commands:
1. Create `newcommand.py` with standard 4-function interface
2. Add module docstring (first line = help)
3. Module auto-discovered and available

Example:
```python
# newcommand.py
"""Manage system settings."""

def init(args, **kwargs) -> bool:
    return True

def access(args, op, **kwargs) -> bool:
    return True

def buildargs(args, **kwargs) -> ArgumentParser | None:
    return None

def main(args, **kwargs) -> bool:
    # Your implementation
    return True
```

---

**End of Comprehensive Specification**

See `console.md` for quick navigation and section links.

