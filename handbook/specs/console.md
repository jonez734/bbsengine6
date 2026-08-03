# Console Module Specification - Index

## Quick Links

| Section | Purpose | File |
|---------|---------|------|
| **Overview** | File inventory, quick reference | `console/overview.md` |
| **Architecture** | Design patterns, execution flow, layering | `console/architecture.md` |
| **Core Library** | lib.py module discovery and helpers | `console/core-library.md` |
| **Main Console** | __main__.py, main.py, stages, menu | `console/main-console.md` |
| **Member Management** | member.py CRUD and editing | `console/member-management.md` |
| **Member Approval** | memberapproval.py approval workflow | `console/member-approval.md` |
| **Session Management** | session.py display and tracking | `console/session-management.md` |
| **Database Checks** | check*.py modules grouped by category | `console/database-checks.md` |
| **Notify Module** | notify.py notification system (stub) | `console/notify.md` |
| **Email Module** | email.py email configuration (incomplete) | `console/email.md` |
| **Data Flows** | Complete workflows with call sequences | `console/data-flows.md` |
| **Dependencies** | Import map and relationships | `console/dependencies.md` |
| **Comprehensive** | Consolidated detailed reference | `console/comprehensive.md` |

---

## Module Summary

The **console module** (`bbsengine6/console/`) provides the administrative command-line interface for BBS Engine 6. It implements:

- **Database initialization** via two-stage setup (prerequisites, then database structure)
- **Member management** with interactive CRUD operations
- **Member approval workflow** for new account processing
- **Session monitoring** for active user tracking
- **System configuration** for email and notifications (incomplete)
- **Plugin architecture** for extensible console commands

**Key Statistics:**
- **Total:** ~2,203 lines across 21 Python modules
- **Entry points:** `__main__.py`, `main.py`
- **Core framework:** `lib.py` (module discovery and execution)
- **Subcommands:** member, session, memberapproval, email, notify
- **Database checks:** 11 verification modules (check*.py)

---

## Getting Started

### For New Developers

1. Start with **Overview** (`console/overview.md`) for file inventory and module structure
2. Read **Architecture** (`console/architecture.md`) for design patterns and execution flow
3. Focus on sections relevant to your task:
   - **Member Management** for user operations
   - **Database Checks** for initialization
   - **Core Library** for understanding module discovery

### For Operations/Deployment

1. **Main Console** (`console/main-console.md`) — Database setup stages
2. **Database Checks** (`console/database-checks.md`) — Verification sequence
3. **Data Flows** (`console/data-flows.md`) — Initialization workflow

### For Maintenance/Debugging

1. **Data Flows** (`console/data-flows.md`) — Call sequences and transaction boundaries
2. **Dependencies** (`console/dependencies.md`) — Import relationships
3. Specific module spec for the component you're debugging

---

## Architecture Highlights

### Module Discovery Pattern

Console modules are auto-discovered from the `bbsengine6/console/` package. To add a new command:

1. Create `newcommand.py` with standard 4-function interface
2. Add module docstring (first line becomes help text)
3. Module is automatically discovered and added to menu

### Stage-Based Initialization

Database setup happens in two stages:

**Stage 0 (Prerequisites):**
- Connect to PostgreSQL system database
- Create/verify roles, functions, user permissions
- Create main BBS database

**Stage 1 (Database Structure):**
- Connect to main BBS database
- Create/verify schema, extensions, functions, tables, flags

### Interactive Menu Pattern

All interactive modules follow:
- Display status → Show menu options → Get user choice → Execute → Return to menu
- Bracket notation for options: `[M]embers`, `[N]ew`, `[E]dit`, `[X]it`
- Input validation with retry

---

## File Organization

```
bbsengine6/console/
├── __init__.py              [1 line]       Module init, exports member
├── __main__.py              [49 lines]     CLI entry point
├── lib.py                   [311 lines]    Module discovery, framework
├── main.py                  [199 lines]    Stages 0-1, interactive menu
├── member.py                [610 lines]    Member CRUD, editing
├── memberapproval.py        [128 lines]    Approval workflow
├── session.py               [85 lines]     Session display
├── notify.py                [25 lines]     Notifications (stub)
├── email.py                 [87 lines]     Email config (incomplete)
├── createdatabase.py        [29 lines]     DB creation utility
└── check*.py (11 files)     [1,074 lines]  Database verification
    ├── checkroles.py                      Verify PostgreSQL roles
    ├── checkwebserverrole.py             Verify www-data role
    ├── checkextensions.py                Verify PG extensions
    ├── checkschema.py                    Verify engine schema
    ├── checkdatabase.py                  Verify/create BBS DB
    ├── checksuperuser.py                 Verify user permissions
    ├── checkfunctions.py                 Verify stored functions
    ├── checkloginid.py                   Verify system login (DBus)
    ├── checkclasses.py                   Verify table structure
    ├── checkflag.py                      Verify flag tables
    └── checknotify.py                    Verify notification system
```

---

## Standard Module Interface

All console modules implement exactly four functions:

```python
def init(args, **kwargs) -> bool:
    """Initialize module (called once at startup)."""

def access(args, op, **kwargs) -> bool:
    """Check user access permissions."""

def buildargs(args, **kwargs) -> ArgumentParser | None:
    """Build CLI argument parser."""

def main(args, **kwargs) -> bool:
    """Execute module functionality."""
```

**Important:** All four functions must accept `**kwargs` for framework compatibility.

---

## Key Workflows

### Add New Member

```
Console menu [M]embers → [N]ew
  → member.add(args)
    → member._edit(args, "add", {})   [interactive form]
    → libmember.insert()              [create member record]
    → libmember.setpassword()         [hash password]
    → libmember.setcredits()          [set credits]
    → libmember.setflag()             [set flags]
    → configurerole()                 [create DB role]
    → conn.commit()
```

### Approve Pending Members

```
Console menu [M]embers → [A]pprovals
  → memberapproval.main(args)
    → Query: SELECT * FROM engine.member WHERE approvedbyid IS NULL
    → For each member:
      - Confirm email verified
      - Confirm approval
      - Set flags: EMAILVERIFIED, APPROVED
      - Update approvedbyid, approveddate
      - conn.commit()
```

### View Active Sessions

```
Console menu [S]essions
  → session.main(args)
    → Query: SELECT * FROM engine.session WHERE expires > NOW()
    → Display: moniker, created, expires, lastactivity
    → Show summary
```

---

## Database Initialization

### Stage 0 Sequence

1. Connect to PostgreSQL system database (`postgres`)
2. `lib.checkroles()` — Create web, sysop, term roles
3. `lib.checkfunctions(stage=0)` — Load core functions
4. `lib.checksuperuser()` — Verify user permissions
5. `lib.checkwebserverrole()` — Create www-data role
6. `lib.createdatabase()` — Create main BBS database

### Stage 1 Sequence

1. Connect to main BBS database (created in stage 0)
2. `lib.checkextensions()` — Create pgcrypto, ltree, citext extensions
3. `lib.checkschema()` — Create engine schema
4. `lib.checkfunctions(stage=1)` — Load engine functions
5. `lib.checkclasses()` — Create tables
6. `lib.checkflag()` — Create flag tables
7. `lib.checknotify()` — Create notification system

---

## Access Control

**memberapproval.py:**
- Requires `SYSOP` flag on current user
- Accessed via `member.checkflag()`
- Returns `False` if non-sysop attempts

---

## Error Handling

### Database Errors

- Query fails → return False, log traceback
- Transaction fails → rollback, return False
- Connection fails → return False, log error

### User Input Errors

- Invalid menu choice → prompt again
- Missing required field → highlight, prompt again
- Duplicate moniker → show error, prompt again

### Stop-on-Failure

- Stage 0/1 errors → entire stage fails, user must fix and restart
- Individual module errors → caught, user can retry or cancel

---

## Dependencies

**External Packages:**
- `psycopg` — PostgreSQL operations
- `dbus` — Linux system integration (checkloginid.py)
- `argparse` — CLI parsing
- `bcrypt` — Password hashing (via libmember)

**Internal (bbsengine6):**
- `bbsengine6.database` — Connection pooling, CRUD
- `bbsengine6.member` — Member entity operations
- `bbsengine6.io` — Input/output
- `bbsengine6.util` — Utilities
- `bbsengine6.session` — Session management
- `bbsengine6.module` — Module framework

---

## Extension Points

Add new console commands by:
1. Creating `bbsengine6/console/newcommand.py`
2. Implementing standard 4-function interface
3. Adding module docstring
4. Module is auto-discovered and available via:
   - `zoidoffice newcommand` (CLI)
   - Console menu (if added to main.py)

---

## Common Tasks

### Check Module Status

- "Is the database initialized?" → Run `main.stage_zero()` and `main.stage_one()`
- "How many members?" → Query `engine.member` in `main.py` status display
- "Who's logged in?" → View sessions via `session.main()`

### Troubleshoot Member Issues

- "Member can't log in" → Check `APPROVED` flag via `member.editflags()`
- "Wrong member credits" → Edit via `member.edit()` and update credits
- "Member needs approval" → Process via `memberapproval.main()`

### Debug Database Issues

- "Schema not created?" → Run `lib.checkschema()` to create/verify
- "Functions missing?" → Run `lib.checkfunctions()` to load
- "Extensions not installed?" → Run `lib.checkextensions()` to create

---

## Incomplete Features

**notify.py** — REMOVED (2026-07-22)
- The `bbsengine6/console/notify.py` module and the
  `bbsengine6/console/checknotify.py` /
  `checknotifyd.py` helpers were **deleted** in Phase 7 of
  `TODO-message-migration.md`. The replacement notification
  system lives in `bbsengine6/message.py` (see
  `handbook/specs/NOTIFY_MESSAGING.md` and the Phase 8 / Phase 9
  entries in `TODO-message-migration.md`).
- The "Incomplete Features" note that previously called this a
  "stub" is now outdated; the subsystem is gone, not stubbed.

**email.py** — Incomplete implementation
- Stub module structure in place
- Database schema not yet defined
- Design: SMTP configuration, email templates, notification delivery

---

## Related Documentation

- **database.md** — Database module (connection, CRUD, schema ops)
- **member.md** — Member entity module (member operations)
- **module.md** — Module framework (module loading and execution)

---

## Comprehensive Consolidated Reference

For offline reading or detailed reference, see `console/comprehensive.md` which consolidates all sections into a single document.

