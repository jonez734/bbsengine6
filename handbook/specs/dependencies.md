# bbsengine6 Module Dependencies Specification

**Version:** 0.0.1.dev  
**Last Updated:** 2026-02-23

This document describes module dependencies, their rationale, and how modules relate to each other.

## Table of Contents

1. [Dependency Matrix](#dependency-matrix)
2. [Layer-to-Layer Dependencies](#layer-to-layer-dependencies)
3. [Inter-Module Dependencies](#inter-module-dependencies)
4. [External Package Dependencies](#external-package-dependencies)
5. [Dependency Rationale](#dependency-rationale)
6. [Circular Dependencies](#circular-dependencies)

---

## Dependency Matrix

### Python Core Modules

```
Legend: → means "depends on"

database.py        → psycopg, psycopg_pool, io.echo
session.py         → database.py, member.py, io.echo
member.py          → database.py, util.py, io.echo
module.py          → database.py, io.echo, importlib
util.py            → io.echo, logging, hashlib
menu.py            → util.py, io.*, database.py
listbox.py         → database.py, util.py, io.*
form.py            → util.py, io.*
editor.py          → io.getch, io.echo, io.screen
input.py           → io.*
blurb.py           → database.py, util.py
folder.py          → database.py
readfile.py        → util.py, io.echo
conf.py            → os (stdlib)
common.py          → logging (stdlib)
engine.py          → [stub, minimal]
screen.py          → io.screen
```

### Dependency Graph (Core)

```
PostgreSQL
    ↑
    │
database.py ←────── session.py
    ↑                   ↑
    │                   │
    │              member.py ←─ util.py ←─ io.echo ←─ terminal.py
    │                   ↑
    │                   │
module.py ←────────────┘
    ↑
    │
menu.py ←─── listbox.py ←─ util.py
    ↑             ↑
    │             │
io.* modules ────┴─────┐
(getch, echo,           │
screen, input*)        folder.py
                        blurb.py
                        editor.py
```

### Python I/O Subpackage

```
echo.py        → terminal.py, palette.py, const.py, echovars.py
screen.py      → terminal.py, const.py
getch.py       → keymap.py
inputstring.py → getch.py, echo.py
inputinteger.py → inputstring.py, echo.py
inputboolean.py → getch.py, echo.py
inputchoice.py  → getch.py, echo.py
terminal.py    → shutil, terminfo (system)
palette.py     → [no dependencies]
keymap.py      → [no dependencies]
const.py       → [no dependencies]
echovars.py    → [no dependencies]
```

### Python Console Subpackage

```
main.py                    → database.py, various check modules
checkdatabase.py           → database.py
checkschema.py             → database.py
checkroles.py              → database.py
checksuperuser.py          → database.py
checkextensions.py         → database.py
checkfunctions.py          → database.py
checkclasses.py            → database.py
checkflag.py               → database.py
createdatabase.py          → database.py
member.py (console)        → database.py, member.py (core)
memberapproval.py          → database.py, member.py
checkloginid.py            → member.py
email.py                   → util.py
alert.py                   → util.py
```

### PHP Modules

```
bootstrap.php    → [sets include path, bbsengine6\bootstrap(array) function]
engine.php       → database.php, session.php, libmember.php, util.php, Smarty
database.php     → PDO, PostgreSQL driver
session.php      → database.php, libmember.php
libmember.php    → database.php, util.php
util.php         → [no dependencies]
InputDate.php    → HTML_QuickForm2
InputDateTime.php → HTML_QuickForm2
InputEmail.php   → HTML_QuickForm2
InputUrl.php     → HTML_QuickForm2
libsig.php       → [utilities]
page.php         → engine.php
blurb.php        → database.php, util.php
```

---

## Layer-to-Layer Dependencies

### Data Layer → Nothing
(Foundation - no upward dependencies)

```
database.py
  └─ External: psycopg, psycopg_pool
```

### Business Logic Layer → Data Layer

```
session.py ──────┐
                 ├──→ database.py
member.py ───────┘
module.py ───────┘
blurb.py ────────┘
folder.py ───────┘
```

**Rationale:**
- All persistence goes through database.py
- Ensures consistent query execution
- Enables centralized error handling
- Allows future database swaps (e.g., MySQL)

### Presentation Layer → Business Logic & Data

```
menu.py ──────────┐
                  ├──→ database.py
listbox.py ───────┤
editor.py ────────┤
form.py ──────────┘

menu.py ──────────┐
                  ├──→ util.py
listbox.py ───────┤
form.py ──────────┘
```

**Rationale:**
- Widgets directly query database for data
- Widgets use utilities for formatting
- No business logic in presentation layer (thin client)

### Module System → Everything

```
module.py ──────→ database.py (access control)
            ├──→ io.echo (error display)
            ├──→ imported modules (dynamic)
            └──→ util.py (helpers)
```

**Rationale:**
- Module system is meta-layer that loads other code
- Must interface with access control
- Must handle errors gracefully

### I/O Subpackage → No upward dependencies

```
io/echo.py
io/screen.py
io/getch.py
etc.
  └─ Only depend on lower-level I/O or system calls
```

**Rationale:**
- I/O is foundation for terminal interface
- Shouldn't create circular dependencies
- Easy to swap with other I/O implementations

---

## Inter-Module Dependencies

### Session ↔ Member Bidirectional

**session.py depends on member.py:**
- Calls `member.getcurrentmoniker()` during session operations
- Needs member info for session validation

**member.py depends on session.py:**
- No direct dependency, but uses shared session globals

**Rationale:**
- Session and member are separate concerns
- Session tracks login state (when/where/how)
- Member tracks identity (who/what)
- Separation allows independent testing

### Module System ↔ Database

**module.py depends on database.py:**
- Queries access control rules before loading module
- Ensures unauthorized modules don't execute

**database.py does NOT depend on module.py:**
- No circular dependency
- Database is lower layer

**Rationale:**
- Security: access control checked first
- Prevents untrusted code execution
- Database doesn't need to know about modules

### Utility Functions (Star Dependencies)

**Many modules depend on util.py:**

```
session.py   ──┐
member.py    ──┤
blurb.py     ──┤──→ util.py
folder.py    ──┤
editor.py    ──┘
form.py      ──┤
menu.py      ──┤
listbox.py   ──┘
```

**Rationale:**
- util.py = shared code library
- Prevents duplication
- Centralized formatting/logging
- Easy to maintain common behavior
- util.py has NO upward dependencies

### I/O Subpackage Dependencies

**All input modules depend on lower-level I/O:**

```
inputinteger.py ──→ inputstring.py ──→ getch.py ──→ keymap.py
inputboolean.py ────→ getch.py ─────────→ keymap.py
inputchoice.py ─────→ getch.py ─────────→ keymap.py
```

**Rationale:**
- Builds abstraction layers from ground up
- char input (getch) → string input → typed input
- Higher levels don't care about key codes
- Easy to replace with different input method

---

## External Package Dependencies

### Python

**Critical (required to run):**
```
psycopg >= 3.0                   (PostgreSQL driver)
  └─ Required for database.py
  
psycopg-pool                     (Connection pooling)
  └─ Required for database.py
```

**Standard Library (always available):**
```
import os, sys, types, logging, argparse, uuid
import datetime, json, copy, pwd, time
import re, hashlib, random, shutil
import importlib, pickle, subprocess
import termios, tty, fcntl, select
```

**Optional (for features):**
```
wcwidth                          (Terminal width calculation)
  └─ Used in io.terminal module
```

### PHP

**Required:**
```
PHP >= 8.1
PDO (PHP Data Objects)
PDO PostgreSQL driver
```

**Libraries:**
```
Smarty >= 3.0                    (Template engine)
PEAR Log                         (Logging)
HTML_QuickForm2                  (Form handling)
ReCaptcha                        (CAPTCHA protection)
```

### JavaScript

**Required:**
```
jQuery >= 3.0                    (DOM manipulation)
```

**Optional:**
```
jquery.smoothState.js            (AJAX page transitions)
TinyMCE >= 5.0                   (Rich text editor)
```

### PostgreSQL

**Version:** 12+

**Required Extensions:**
```
ltree                            (Hierarchical data)
uuid-ossp                        (UUID generation)
```

**Optional Features:**
```
JSON support (built-in)
JSONB support (for flexibility)
Roles/permissions system
```

---

## Dependency Rationale

### Why database.py has no upward dependencies

**Benefit:**
- Can be replaced with any database backend
- Tests can mock database without mocking whole system
- Database changes don't break business logic

**Example swap:**
```python
# Current: PostgreSQL
database.connect() → psycopg

# Could swap to: MySQL, SQLite, etc.
database.connect() → mysql.connector
# Rest of code doesn't change
```

### Why util.py is widely used

**Benefit:**
- Single source of truth for common operations
- Easy to fix bugs (fix once, everywhere benefits)
- Consistent formatting across all modules
- Easy to add logging/debugging

**Example:**
```python
# If you fix pluralize() bug in util.py
# It's fixed everywhere it's used:
menu.py, listbox.py, form.py, all benefit
```

### Why session.py and member.py are separate

**Benefit:**
- Can test member authentication independently
- Can test session management independently
- Can trace session issues without member code
- Supports multiple authentication schemes

**Example:**
```
If adding OAuth:
  ├─ Keep session.py unchanged
  ├─ Modify member.py to support OAuth
  └─ No ripple effects in session code
```

### Why module.py is meta-layer

**Benefit:**
- Modules are black boxes
- module.py doesn't need to know module internals
- Modules don't depend on module.py
- Easy to add new modules without changing framework

**Example:**
```
Adding new module:
  ├─ Create my_module/__init__.py
  ├─ Implement: init(), access(), buildargs(), main()
  └─ module.py loads it automatically
  
No changes to module.py needed!
```

### Why io module is isolated

**Benefit:**
- Terminal I/O details hidden
- Can swap with web/GUI without changing callers
- Testable independently
- Easy to add new input/output types

**Example:**
```
# Current: Terminal
io.echo() → writes to sys.stdout
io.getch() → reads from sys.stdin

# Could be: Web
io.echo() → returns JSON
io.getch() → expects HTTP POST

# Callers don't change!
```

---

## Circular Dependencies

### Current Status: NONE

bbsengine6 has **no circular dependencies**.

This is achieved through:

**1. Clear layer separation**
```
Lower layers don't know about upper layers
  Database ← Business Logic ← Presentation
    ↑           ↑
    └─ No upward dependencies
```

**2. Module system is meta**
```
module.py loads other modules dynamically
  Other modules don't load module.py
  No circular reference
```

**3. Shared utilities pattern**
```
util.py is shared code
Many modules use util.py
util.py doesn't import any of them
  No circular imports
```

**4. Explicit initialization order**
```
Session needs Member data
  Member module can be loaded first
  Session initialized after
  No circular initialization
```

### How to Maintain This

When adding new modules:

1. **Check dependency direction**
   ```python
   # Good: lower depends on upper
   util.py → nothing
   database.py → util.py
   session.py → database.py
   
   # Bad: upper depends on lower (AVOID)
   database.py → session.py  # DON'T DO THIS
   ```

2. **Use message passing instead of direct calls**
   ```python
   # Instead of:
   # module_a imports module_b
   # module_b imports module_a
   
   # Use:
   # Pass data through callbacks
   # Use events/signals
   # Use dependency injection
   ```

3. **Refactor if cycles appear**
   ```python
   # If cycle detected:
   # module_a ← module_b ← module_a
   
   # Solution: Extract common code to shared module
   # module_a ← common ← module_b
   #           (no cycle)
   ```

---

## Dependency Metrics

### Coupling Analysis

**Low Coupling (Good):**
- database.py: only depends on external libs
- util.py: only depends on stdlib
- io modules: only depend on other io modules

**Medium Coupling (Acceptable):**
- session.py: depends on database, member
- menu.py: depends on database, io, util
- module.py: depends on database, io, importlib

**High Coupling (Monitor):**
- engine.php: depends on many PHP modules
- Action: Could be refactored if grows much larger

### Reusability Rank

**Highest Reusability:**
1. database.py - used by everything
2. util.py - used by most modules
3. io modules - core for terminal interface
4. session.py - critical for auth

**Medium Reusability:**
5. member.py - auth
6. menu.py, listbox.py - widgets
7. module.py - plugin system

**Specific Use:**
8. editor.py, form.py - specific features
9. blurb.py, folder.py - message domain

---

## Cross-Deployment Dependencies

### Terminal Application

Required modules:
```
database.py          (database access)
session.py, member.py (auth)
module.py             (plugin system)
util.py               (utilities)
io/*                  (terminal I/O)
menu.py, listbox.py   (widgets)
editor.py, form.py    (editing)
blurb.py, folder.py   (messages)
```

### Web Application (PHP)

Required modules:
```
engine.php            (request handling)
database.php          (database access)
session.php, libmember.php (auth)
util.php              (utilities)
Smarty                (templates)
InputDate, etc.       (form elements)
```

### Console Tools

Required modules:
```
database.py           (database access)
console/*             (admin tools)
util.py               (utilities)
```

### Shared Layer

Used by multiple deployments:
```
PostgreSQL            (database backend)
member table          (user data)
__session table       (session data)
```

---

## Performance Implications

### Connection Pooling

**database.py uses psycopg_pool:**
- Reduces connection overhead
- Reuses connections across requests
- Limits max connections (20)

**Impact:**
- First query: slight overhead (pool setup)
- Subsequent: minimal overhead (connection reuse)
- Concurrent: up to 20 queries in parallel

### Caching Opportunities

**Not yet implemented, but possible:**

```python
# Cache member flags during session
member.getflags()  # Could cache for duration of session
  └─ Cache hit: O(1)
  └─ Cache miss: O(database query)

# Cache OID lookups
database.getoid()  # Should cache results in conf.py
  └─ Current: queries each time
  └─ Optimal: query once, cache forever
```

### Query Optimization Potential

**Indexes on frequently accessed columns:**
```sql
CREATE INDEX idx_member_loginid ON engine.member(loginid);
CREATE INDEX idx_session_id ON engine.__session(id);
CREATE INDEX idx_blurb_folderid ON engine.__blurb(folderid);
```

**Currently assumed but not documented.**

---

*Module Dependencies Specification for bbsengine6*
