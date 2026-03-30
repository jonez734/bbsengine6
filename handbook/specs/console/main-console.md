# Main Console Entry Points

## Overview

`__main__.py` and `main.py` provide the console application entry point and database initialization framework.

**Files:**
- `bbsengine6/console/__main__.py` — 49 lines, CLI entry point
- `bbsengine6/console/main.py` — 199 lines, initialization stages and interactive menu

---

## __main__.py: CLI Entry Point

### Entry Point Function

```python
if __name__ == "__main__":
    # Parse arguments
    # Discover modules
    # Route to subcommand or interactive console
```

**Behavior:**
1. Creates `ArgumentParser` with program description
2. Calls `lib.build_subcommand_parser()` to add discovered modules as subcommands
3. Parses command-line arguments
4. If subcommand provided: routes to `lib.handle_subcommand(args, subcommand)`
5. If no subcommand: defaults to `lib.runmodule(args, "console.main")`

**Execution Paths:**
```
zoidoffice member --help
  → Loads member module's parser and shows help

zoidoffice member --add --moniker alice
  → Loads member module with arguments

zoidoffice
  → Defaults to console.main (interactive menu)
```

---

## main.py: Initialization & Interactive Console

### Standard Module Interface

```python
def init(args, **kwargs) -> bool:
    """Initialize console module."""

def access(args, op, **kwargs) -> bool:
    """Check access (stub, returns True)."""

def buildargs(args, **kwargs) -> ArgumentParser | None:
    """Return None (main console has no CLI args)."""

def main(args, **kwargs) -> bool:
    """Run console: stages 0-1, then interactive menu."""
```

---

### stage_zero()

```python
def stage_zero(args, **kwargs) -> bool
```

Database setup prerequisites. Executed once at startup.

**Steps:**
1. Connect to PostgreSQL `postgres` database (system database)
2. `lib.checkroles()` — Verify/create roles: web, sysop, term
3. `lib.checkfunctions(stage=0)` — Verify/create core functions
4. `lib.checksuperuser()` — Verify current user has superuser rights
5. `lib.checkwebserverrole()` — Verify www-data role exists
6. `lib.createdatabase()` — Create main BBS database if not exists

**Returns:** `True` if all checks pass, `False` on first failure

**Connection:** Creates separate connection to `postgres` database via `database.connect()`

**Failure Mode:** Stops on first failure; user must fix environment and restart

---

### stage_one()

```python
def stage_one(args, **kwargs) -> bool
```

Database structure and function initialization. Executed after stage 0 succeeds.

**Steps:**
1. Connect to main BBS database (created in stage 0)
2. `lib.checkextensions()` — Verify/create extensions: pgcrypto, ltree, citext
3. `lib.checkschema()` — Verify/import engine schema
4. `lib.checkfunctions(stage=1)` — Verify/create engine functions
5. `lib.checkclasses()` — Verify/create class definitions (tables)
6. `lib.checkflag()` — Verify/initialize system flags
7. `lib.checknotify()` — Verify/initialize notification system

**Returns:** `True` if all checks pass, `False` on first failure

**Connection:** Creates new connection to BBS database

**Isolation:** Uses separate transactions for each check operation

---

### Interactive Menu

```python
def main(args, **kwargs) -> bool
```

After successful initialization (stages 0–1), displays interactive console menu.

**Behavior:**
1. Displays header with database info:
   - Member count (from `engine.member` table)
   - Database size
   - Connection status
2. Displays menu options
3. Prompts for user choice
4. Executes selected action
5. Returns to menu (loops until exit)

**Menu Options:**

| Option | Action | Handler |
|--------|--------|---------|
| [M]embers | Manage members | `member.main(args, pool=pool)` |
| [S]essions | View active sessions | `session.main(args, pool=pool)` |
| [X]it | Exit console | `return True` |

**Status Display:**
```
BBS Engine 6 Console
====================
Database: bbsengine6
Members: 42
Status: Online

[M]embers  [S]essions  [X]it
```

**Input Handling:**
- Uses `io.inputchoice()` for menu selection
- Valid choices are case-insensitive first character (M, S, X)
- Invalid choices prompt again
- Displays selected option feedback before executing

---

## Error Handling & Recovery

### Stage 0 Failure

If stage 0 fails (e.g., superuser check):
1. Error is logged and displayed
2. Console exits with failure
3. User must fix PostgreSQL configuration or permissions
4. Restart console to retry

### Stage 1 Failure

If stage 1 fails (e.g., schema import):
1. Error is logged and displayed
2. Depends on operation type:
   - Extension install fails → exit, user must enable on PostgreSQL
   - Schema import fails → exit, user must check SQL file
   - Function creation fails → exit, user must check function SQL

### Interactive Menu Error

If menu handler fails (member.py, session.py):
1. Error is caught and displayed
2. Menu returns and prompts again
3. No data corruption (transaction rolled back)

---

## Connection Management

**Stage 0:**
```python
with database.connect(args, pool=pool) as conn:
    # Use separate connection to 'postgres' database
    # Multiple cursor contexts for different operations
    conn.commit()  # or rollback on error
```

**Stage 1:**
```python
with database.connect(args, pool=pool) as conn:
    # Use separate connection to BBS database
    # Multiple cursor contexts for schema, functions, classes, etc.
```

**Interactive Loop:**
```python
pool = database.getpool(args)  # Once at startup
# Pass pool to submodules
member.main(args, pool=pool)
session.main(args, pool=pool)
```

---

## Data Access

### Member Count

Queries `engine.member` table:
```python
with database.cursor(conn) as cur:
    cur.execute("SELECT COUNT(*) as count FROM engine.member")
    result = cur.fetchone()
    member_count = result['count']
```

### Database Info

From PostgreSQL system tables:
```python
# Database size
# Connection status
# Last activity timestamp
```

---

## Dependencies

**Internal:**
- `bbsengine6.console.lib` — Wrapper functions for all checks
- `bbsengine6.console.member` — Member management module
- `bbsengine6.console.session` — Session display module
- `bbsengine6.database` — Connection pooling and queries
- `bbsengine6.io` — Input/output functions
- `bbsengine6.util` — Utility functions

**External:**
- `psycopg` — PostgreSQL operations
- `argparse` — Argument parsing

