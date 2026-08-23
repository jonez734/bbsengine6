# Dependencies & Module Relationships

## Overview

This section documents all internal and external dependencies, import relationships, and module interactions.

---

## External Dependencies

### Standard Library

| Module | Used By | Purpose |
|--------|---------|---------|
| `argparse` | `__main__.py`, `lib.py`, all console modules | CLI argument parsing |
| `copy` | `member.py` | Deep copy for change tracking in edit form |
| `datetime` | `session.py`, `memberapproval.py` | Timestamp handling |
| `importlib` | `lib.py` | Dynamic module loading |
| `inspect` | `lib.py` | Signature inspection |
| `pkgutil` | `lib.py` | Package directory scanning |
| `sys` | `__main__.py` | System functions |
| `typing` | `lib.py`, all modules | Type hints |

### Third-Party Packages

| Package | Used By | Purpose |
|---------|---------|---------|
| `psycopg` | All check modules, `member.py`, `session.py`, `memberapproval.py` | PostgreSQL connection and operations |
| `bcrypt` | `member.py` (via libmember) | Password hashing |
| `dbus` | `checkloginid.py` | Linux DBus system integration |
| `argcomplete` | `__main__.py` | CLI argument auto-completion |

---

## Internal Dependencies: bbsengine6 Modules

### Core Framework

```
bbsengine6.database
  ├─ Used by: all check modules, member.py, session.py, memberapproval.py, main.py
  ├─ Purpose: Connection pooling, CRUD operations, schema management
  ├─ Key functions:
  │  ├─ getpool() — Create connection pool
  │  ├─ connect() — Get connection from pool
  │  ├─ cursor() — Create dict-row cursor
  │  ├─ update() — Update rows
  │  ├─ insert() — Insert rows
  │  └─ select() — Query rows
  └─ Return types: bool, dict, list[dict]

bbsengine6.io
  ├─ Used by: all modules
  ├─ Purpose: Input/output formatting and user interaction
  ├─ Key functions:
  │  ├─ echo() — Print formatted text
  │  ├─ echo_traceback() — Print exception traceback
  │  ├─ inputchoice() — Menu selection
  │  ├─ inputboolean() — Yes/no prompt
  │  ├─ inputtext() — Text input
  │  └─ color formatting
  └─ Return types: str, bool, None

bbsengine6.module
  ├─ Used by: lib.py, __main__.py
  ├─ Purpose: Module loading and execution framework
  ├─ Key functions:
  │  ├─ load() — Load module by path
  │  ├─ run() — Execute module lifecycle
  │  └─ check() — Validate module
  └─ Return types: module, bool, Any

bbsengine6.util
  ├─ Used by: member.py, session.py, all check modules
  ├─ Purpose: Utility functions
  ├─ Key functions:
  │  ├─ Encryption/decryption
  │  ├─ String formatting
  │  └─ Date/time utilities
  └─ Return types: str, bool, datetime
```

### Domain-Specific Modules

```
bbsengine6.member (imported as libmember)
  ├─ Used by: member.py, memberapproval.py
  ├─ Purpose: Member entity operations
  ├─ Key functions:
  │  ├─ find(moniker) — Get member record
  │  ├─ insert() — Create new member
  │  ├─ update() — Update member
  │  ├─ setpassword() — Hash and store password
  │  ├─ setcredits() — Set member credits
  │  ├─ setflag() — Set member flag
  │  ├─ checkflag() — Check if member has flag
  │  └─ getflags() — Get all member flags
  └─ Return types: dict, bool, list[str]

bbsengine6.session
  ├─ Used by: main.py, session.py
  ├─ Purpose: Session management
  ├─ Key functions:
  │  ├─ list_sessions() — Get active sessions
  │  ├─ create_session() — Create new session
  │  ├─ update_lastactivity() — Update session activity
  │  └─ expire_session() — End session
  └─ Return types: dict, list[dict], bool
```

---

## Internal Dependencies: Console Module

### Local Imports

All console modules import from `bbsengine6.console.lib`:

```python
from . import lib

# Available functions:
lib.discover_console_modules()
lib.validate_module_for_discovery()
lib.clear_module_cache()
lib.build_subcommand_parser()
lib.handle_subcommand()
lib.runmodule()
lib.setbottombar()
lib.checkroles()
lib.checkextensions()
lib.checkdatabase()
lib.checksuperuser()
lib.checkfunctions()
lib.checkwebserverrole()
lib.checkschema()
lib.checkclasses()
lib.checkpasswordformat()
lib.checkflag()
lib.checkloginid()
lib.checknotify()
```

### Cross-Module Dependencies

**member.py** imports:
```python
from bbsengine6 import database, io, member as libmember, util
from . import lib
from . import memberapproval  # For [A]pprovals menu option
```

**memberapproval.py** imports:
```python
from bbsengine6 import database, io, member, util
from . import lib
```

**session.py** imports:
```python
from bbsengine6 import database, member, util
from . import lib
```

**main.py** imports:
```python
from bbsengine6 import database, io, member, session, util
from . import lib, member, session
```

**All check modules** import:
```python
from bbsengine6 import database, io, util
from . import lib
```

---

## Import Graph

```
__main__.py
  ├─ bbsengine6.module.run()
  ├─ argparse
  ├─ argcomplete
  └─ console.lib (indirect via module.run)

lib.py
  ├─ importlib
  ├─ inspect
  ├─ pkgutil
  ├─ bbsengine6.module
  └─ bbsengine6.io

main.py
  ├─ bbsengine6.database
  ├─ bbsengine6.io
  ├─ bbsengine6.member
  ├─ bbsengine6.session
  ├─ bbsengine6.util
  ├─ console.lib (check* wrappers)
  ├─ console.member
  └─ console.session

member.py
  ├─ copy
  ├─ argparse
  ├─ bbsengine6.database
  ├─ bbsengine6.io
  ├─ bbsengine6.member (as libmember)
  ├─ bbsengine6.util
  ├─ console.lib
  └─ console.memberapproval

memberapproval.py
  ├─ bbsengine6.database
  ├─ bbsengine6.io
  ├─ bbsengine6.member
  ├─ bbsengine6.util
  └─ console.lib

session.py
  ├─ datetime
  ├─ argparse
  ├─ bbsengine6.database
  ├─ bbsengine6.member
  ├─ bbsengine6.util
  └─ console.lib

check*.py (all)
  ├─ argparse
  ├─ bbsengine6.database
  ├─ bbsengine6.io
  ├─ bbsengine6.util
  ├─ console.lib
  └─ psycopg (for exceptions)
```

---

## Data Flow Across Modules

### Connection Pool Flow

```
main.py
  └─ pool = database.getpool(args)
     └─ Passed to submodules via **kwargs
        ├─ member.main(args, pool=pool)
        │  └─ With database.connect(args, pool=pool) as conn:
        ├─ session.main(args, pool=pool)
        │  └─ With database.connect(args, pool=pool) as conn:
        └─ memberapproval.main(args, pool=pool)
           └─ With database.connect(args, pool=pool) as conn:
```

### Member Data Flow

```
member.py (add)
  └─ member = {} (user fills form)
     └─ libmember.insert(moniker, loginid, email)
        └─ Returns member dict with ID
        └─ Pass to libmember.setpassword()
           └─ Pass to libmember.setcredits()
              └─ Pass to libmember.setflag() (multiple calls)
```

### Flag Data Flow

```
libmember.setflag()
  └─ INSERT INTO engine.map_member_flag
     └─ Queried by libmember.checkflag()
        └─ Queried by memberapproval.access()
           └─ Returns bool for access control
```

### Session Data Flow

```
database.select(table="engine.session")
  └─ Returns list[dict]
     └─ session.py iterates and formats
        └─ Displayed to user
```

---

## Dependency Injection Pattern

### Connection Pool

```python
# In main.py
pool = database.getpool(args)

# Passed to submodules
member.main(args, pool=pool)
session.main(args, pool=pool)

# In submodule
def main(args, **kwargs):
    pool = kwargs.get('pool')
    with database.connect(args, pool=pool) as conn:
        ...
```

### Arguments Object

```python
# args object passed through call stack
main(args)
  └─ member.main(args, ...)
     └─ member._edit(args, ...)
        └─ database.connect(args, ...)
```

---

## Circular Dependency Analysis

**Potential Circular Dependencies:**
- member.py imports memberapproval (for menu option)
- memberapproval doesn't import member.py ✓ (no circle)

**Safe Structure:**
- Check modules don't import each other ✓
- main.py imports member.py and session.py ✓ (unidirectional)
- member.py imports memberapproval ✓ (unidirectional)
- No cycles detected ✓

---

## Module Initialization Order

### Startup Sequence

```
1. Python starts bbsengine6.console.__main__
2. Import bbsengine6.module
3. bbsengine6.module.run("console.main")
4. Import bbsengine6.console.main
5. main.init(args)
6. main.buildargs(args) → returns None
7. main.main(args)
   └─ Import bbsengine6.console.lib
   └─ lib.runmodule(args, "console.checkroles")
   └─ ...imports each check module as needed
8. Import bbsengine6.console.member (on user selection)
9. Import bbsengine6.console.memberapproval (on [A] selection)
10. Import bbsengine6.console.session (on [S] selection)
```

**Lazy Loading:** Submodules imported only when used

---

## Dependency Management

### Connection Pooling

```
pool created once per console session
  └─ Passed through **kwargs to all submodules
  └─ Reused across multiple operations
  └─ Closed on console exit
```

### Database Transactions

```
Each operation starts own transaction
  └─ COMMIT on success
  └─ ROLLBACK on error
  └─ Pool connection returned for reuse
```

### Module Cache

```
lib.discover_console_modules()
  └─ Results cached in module-level variable
  └─ Clear on --debug flag: lib.clear_module_cache()
```

