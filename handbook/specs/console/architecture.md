# Console Architecture & Design Patterns

## Overview

The console module uses a modular, plugin-based architecture with standardized interfaces. It implements stage-based initialization, dynamic module discovery, transaction-safe database operations, and an interactive menu framework.

---

## Core Design Patterns

### 1. Standard Module Interface

Every console module implements exactly four functions:

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

**Purpose:**
- `init()` — One-time initialization (currently returns `True`)
- `access(op)` — Authorization check with operation type (e.g., `op="run"`)
- `buildargs()` — Define and return argument parser; returns `None` if no CLI support
- `main()` — Execute module logic

**Requirements:**
- All four functions must accept `**kwargs` for framework compatibility
- Modules are discovered by inspecting the console package for files containing these functions
- Module docstring's first line becomes the help text

### 2. Module Discovery Pattern

`lib.discover_console_modules()` automatically discovers valid modules:

1. Scans `bbsengine6/console/` directory for `.py` files
2. Validates each module:
   - Has `main()` function (callable)
   - Has module docstring (for help text)
   - Passes `validate_module_for_discovery()` checks
3. Caches results (cleared in debug mode)
4. Returns list of valid module names

**Benefits:**
- No hardcoded module registry
- Add new module → automatically available
- Zero configuration required

### 3. Stage-Based Initialization

Database initialization uses two distinct stages:

**Stage 0 — Prerequisites**
- Establish connection to `postgres` system database
- Check/create PostgreSQL roles (web, sysop, term)
- Verify superuser permissions
- Verify www-data role
- Create/verify main BBS database

**Stage 1 — Database Setup**
- Connect to main BBS database
- Check/create extensions (pgcrypto, ltree, citext)
- Import/verify schema
- Import/verify stored functions
- Initialize class/table structure
- Initialize system flags
- Verify notification system

**Rationale:**
- Granular control: can restart at any stage
- Transaction isolation: multiple connections prevent locking
- Prerequisite validation: ensures environment before deeper initialization

### 4. Transaction Management Pattern

All database operations follow strict transaction control:

```python
with database.connect(args, pool=pool) as conn:
    with database.cursor(conn) as cur:
        # Execute operations
    conn.commit()  # Explicit commit on success
    # or
    conn.rollback()  # Explicit rollback on error
```

**Rules:**
- Always use context managers for connections and cursors
- Commit/rollback explicitly (don't auto-commit)
- Multiple transactions per operation (each stage is separate)
- Read-only queries don't require explicit commit

**Benefit:** Prevents partial updates and maintains data consistency

### 5. Interactive Menu Pattern

All interactive modules follow a consistent navigation model:

```
Display Status/Data
┌─────────────────────────────────┐
│ [M]embers  [S]essions  [X]it    │
└─────────────────────────────────┘
User selects option → Execute submenu → Return to menu
```

**Features:**
- Bracket notation for options: `[M]`, `[N]`, `[E]`, `[X]`
- Status bar at top (member count, database info)
- Loop until user selects exit
- Input validation with retry on invalid choice

**Implementation:**
- Uses `io.inputchoice()` for menu selection
- Uses `io.inputboolean()` for yes/no prompts
- Uses `io.inputtext()` for text entry
- Colors via template format: `{var:labelcolor}`, `{var:valuecolor}`

### 6. Deep Copy Comparison Pattern (member.py)

Member editing tracks changes through deep copy comparison:

```python
import copy
original = copy.deepcopy(_member)
# User edits _member object
# Display shows fields where original != _member
# Only changed fields highlighted in UI
```

**Use Case:** Interactive edit interface shows "before/after" values

### 7. Wrapper Function Pattern (lib.py)

`lib.py` exports wrapper functions for each check module:

```python
def checkroles():
    return runmodule(args, "console.checkroles")

def checkextensions():
    return runmodule(args, "console.checkextensions")

# ... etc for all check* modules
```

**Purpose:** Provides convenient shortcuts while maintaining consistency

### 8. Connection Pool Passing Pattern

Database connections are passed through `**kwargs`:

```python
pool = database.getpool(args)
lib.runmodule(args, "member", pool=pool, **kwargs)
# member.py receives pool in **kwargs
```

**Benefit:** Avoids creating new connections; reuses pool across modules

---

## Execution Flow

### Entry Point: CLI (zoidoffice command)

```
main
  │
  ├─ Parse arguments with argcomplete
  │   └─ If subcommand (member, email, etc):
  │       ├─ lib.discover_console_modules()
  │       ├─ lib.build_subcommand_parser()
  │       └─ lib.handle_subcommand(args, "member")
  │           └─ lib.runmodule(args, "console.member")
  │               ├─ member.init(args)
  │               ├─ member.buildargs(args)
  │               ├─ parse_args()
  │               └─ member.main(args)
  │
  └─ If no subcommand or "main":
      └─ lib.runmodule(args, "console.main")
          └─ main.main(args)
              ├─ main.stage_zero(args)   [DB setup]
              │   ├─ Connect to postgres DB
              │   ├─ lib.checkroles()
              │   ├─ lib.checkfunctions(stage=0)
              │   ├─ lib.checksuperuser()
              │   ├─ lib.checkwebserverrole()
              │   └─ lib.createdatabase()
              │
              ├─ main.stage_one(args)    [DB init]
              │   ├─ Connect to BBS DB
              │   ├─ lib.checkextensions()
              │   ├─ lib.checkschema()
              │   ├─ lib.checkfunctions(stage=1)
              │   ├─ lib.checkclasses()
              │   ├─ lib.checkflag()
              │   └─ lib.checknotify()
              │
              └─ Interactive Loop:
                  ├─ Display member count + DB info
                  ├─ Menu: [M]embers [S]essions [X]it
                  │
                  ├─ [M] → member.main(args, pool=pool)
                  │   ├─ Menu: [N]ew [E]dit [A]pprovals [Q]uit
                  │   │
                  │   ├─ [N] → member.add(args)
                  │   │   ├─ member._edit(args, "add", {})
                  │   │   ├─ member.configurerole(args, moniker, sysop)
                  │   │   └─ conn.commit()
                  │   │
                  │   ├─ [E] → member.edit(args)
                  │   │   ├─ Select member by moniker
                  │   │   ├─ member._edit(args, "edit", member)
                  │   │   └─ conn.commit()
                  │   │
                  │   ├─ [A] → memberapproval.main(args)
                  │   │   ├─ Query pending approvals
                  │   │   └─ For each: verify email, approve, set flags
                  │   │
                  │   └─ [Q] → Return to main menu
                  │
                  ├─ [S] → session.main(args)
                  │   ├─ Query engine.session table
                  │   └─ Display: moniker, created, expires, lastactivity
                  │
                  └─ [X] → Exit
```

---

## Layering & Separation of Concerns

**Layer 1: Entry Point**
- `__main__.py` — Argument parsing, subcommand routing
- Thin wrapper around `lib.runmodule()`

**Layer 2: Framework & Discovery**
- `lib.py` — Module discovery, validation, execution
- Provides utilities (`checkroles()`, `checkextensions()`, etc.)

**Layer 3: Core Functionality**
- `main.py` — Database initialization (stages 0–1)
- `member.py` — Member CRUD and editing
- `memberapproval.py` — Approval workflow
- `session.py` — Session display
- `email.py` — Email config (stub)
- `notify.py` — Notification config (stub)

**Layer 4: Database Operations**
- `check*.py` — Database verification and setup
- Verify/create roles, extensions, schema, functions, classes, flags

**Layer 5: External Services**
- `bbsengine6.database` — PostgreSQL connection pooling and queries
- `bbsengine6.member` — Member entity operations
- `bbsengine6.io` — Input/output formatting
- `bbsengine6.util` — Utility functions

---

## Key Architectural Decisions

### Why Stage-Based Initialization?

Instead of a linear setup sequence, stage-based allows:
1. Separation of "environment prerequisites" from "application setup"
2. Ability to recover from partial failure by restarting at stage
3. Clear ownership: stage 0 = PostgreSQL system, stage 1 = BBS database

### Why Dynamic Module Discovery?

Hardcoding module registry creates:
- Brittle coupling between framework and modules
- Requires changes to framework when adding modules
- Dynamic discovery = zero overhead for extensibility

### Why Wrapper Functions in lib.py?

`lib.checkroles()` wraps `runmodule(args, "console.checkroles")` to:
- Provide convenient shortcuts for setup stages
- Maintain consistent error handling
- Allow mocking/testing without direct imports

### Why Transaction Isolation Per Stage?

Multiple transactions in `stage_zero()` and `stage_one()`:
- Prevents long-running transactions
- Isolates failures to specific operation
- Allows partial recovery

---

## Error Handling Strategy

**Module Discovery Errors:**
- Module import fails → logged, skipped, continues
- Module validation fails → not added to subcommand list

**Access Control Errors:**
- `access()` returns False → operation blocked, error logged
- `access()` raises exception → caught, traced, denied

**Database Errors:**
- Connection fails → return False, log traceback
- Query fails → rollback, return False, log traceback
- Transaction fails → rollback entire stage, can retry from start

**User Input Errors:**
- Invalid choice in menu → prompt again
- Invalid argument to CLI → show help and exit
- Missing required field in form → highlight, prompt again

---

## Extension Points

The architecture supports extensibility at:

1. **New Console Modules** — Add `newfeature.py` with standard 4 functions
2. **New Check Operations** — Add `checknewdb.py` in standard check pattern
3. **New Menu Options** — Edit `main.py` to call new modules
4. **Database Initialization** — Add new stage or extend existing check modules
5. **Access Control** — Extend `access()` functions with role-based logic

