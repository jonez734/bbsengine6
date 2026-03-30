# Console Module Overview

## Quick Summary

The console module provides the administrative command-line interface for bbsengine6. It handles database initialization, member management, session monitoring, and system configuration through both interactive menus and subcommand-based CLI access.

**Total Lines:** ~2,203  
**Total Files:** 21 Python modules  

---

## File Inventory

### Core Framework (4 files)

| File | Lines | Purpose |
|------|-------|---------|
| `__init__.py` | 1 | Module initialization; exports `member` |
| `__main__.py` | 49 | CLI entry point; argument parsing and subcommand routing |
| `lib.py` | 311 | Module discovery, validation, and execution framework |
| `main.py` | 199 | Interactive console menu; database initialization stages |

### Member Management (3 files)

| File | Lines | Purpose |
|------|-------|---------|
| `member.py` | 610 | Member CRUD operations; interactive editing interface |
| `memberapproval.py` | 128 | Member application approval workflow |
| `notify.py` | 25 | Notification system management (stub) |

### Database Verification (11 files)

**Role Management:**
- `checkroles.py` (43) — Verify/create PostgreSQL roles (web, sysop, term)
- `checkwebserverrole.py` (48) — Verify www-data role exists

**Extensions & Schema:**
- `checkextensions.py` (46) — Verify/install required PG extensions (pgcrypto, ltree, citext)
- `checkschema.py` (39) — Verify/import database schema

**Database & User Validation:**
- `checkdatabase.py` (78) — Verify/create main BBS database
- `checksuperuser.py` (55) — Verify superuser permissions
- `checkloginid.py` (95) — Verify system login ID via DBus

**Functions & Procedures:**
- `checkfunctions.py` (61) — Verify/import stored procedures and functions

**Data Structures:**
- `checkclasses.py` (57) — Verify/initialize database classes/tables
- `checkflag.py` (74) — Verify/initialize system flags
- `checknotify.py` (83) — Verify notification system schema

**Utility:**
- `createdatabase.py` (29) — Database creation helper

### Other (3 files)

| File | Lines | Purpose |
|------|-------|---------|
| `session.py` | 85 | Display and manage active user sessions |
| `email.py` | 87 | Email configuration (incomplete) |
| `lib.py` | 311 | [core library, listed above] |

---

## Key Classes & Functions

### Module Discovery & Execution (`lib.py`)

```python
def discover_console_modules(args, force_refresh=False) -> list
def validate_module_for_discovery(module_fullname) -> bool
def build_subcommand_parser(parser, **kwargs) -> None
def handle_subcommand(args, subcommand, **kwargs) -> bool
def runmodule(args, submodule, **kwargs) -> Any
```

### Database Initialization (`main.py`)

```python
def stage_zero(args, **kwargs) -> bool
def stage_one(args, **kwargs) -> bool
def main(args, **kwargs) -> bool
```

### Member Operations (`member.py`)

```python
def add(args, **kwargs) -> bool
def edit(args, **kwargs) -> bool
def _edit(args, mode, member, **kwargs) -> bool
def editflags(args, moniker, **kwargs) -> bool
def editui(args, rolename) -> bool
def configurerole(args, rolename, sysop, **kwargs) -> bool
def setui(args, rolname, ui, **kwargs) -> bool
def main(args, **kwargs) -> bool
```

### Approval Workflow (`memberapproval.py`)

```python
def main(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
```

### Session Display (`session.py`)

```python
def main(args, **kwargs) -> bool
```

---

## Standard Module Interface

All console modules implement the standard 4-function interface:

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

All four functions **must accept `**kwargs`** for framework compatibility.

---

## Execution Paths

### Interactive Mode

```
zoidoffice [no args]
  → lib.runmodule("main")
    → main.stage_zero()    [DB setup]
    → main.stage_one()     [DB init]
    → Interactive menu loop
```

### Subcommand Mode

```
zoidoffice member [args]
  → lib.discover_console_modules()
  → lib.handle_subcommand("member")
    → member.runmodule()
```

### Direct Module Execution

```
from bbsengine6.console import member
member.main(args, **kwargs)
```

---

## Dependencies

**External Packages:**
- `argparse` — CLI argument parsing
- `psycopg` — PostgreSQL connection and operations
- `dbus` — System integration (Linux-specific)

**Internal (bbsengine6):**
- `bbsengine6.database` — Database connection, CRUD, schema ops
- `bbsengine6.member` — Member entity operations
- `bbsengine6.io` — Input/output formatting and display
- `bbsengine6.util` — Utility functions
- `bbsengine6.session` — Session management
- `bbsengine6.module` — Module framework and execution

**Local (within console):**
- `from . import lib` — Module discovery and execution helpers

---

## Quick Reference: Module Categories

| Category | Files | Purpose |
|----------|-------|---------|
| **Entry Points** | `__main__.py`, `main.py` | CLI and interactive console |
| **Framework** | `lib.py` | Module discovery, validation, routing |
| **User Management** | `member.py`, `memberapproval.py` | Member CRUD and approval |
| **Monitoring** | `session.py` | Active sessions display |
| **DB Verification** | `check*.py`, `createdatabase.py` | Database initialization and validation |
| **Configuration** | `email.py`, `notify.py` | System settings (incomplete) |

