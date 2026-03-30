# Database Checks & Verification Modules

## Overview

All `check*.py` modules verify and initialize database components during console startup. They follow a consistent pattern: check if component exists, create if missing, return True/False status.

**Total:** 11 check modules (1,074 lines)  
**Used by:** `main.py` stages 0 and 1

---

## Common Pattern

All check modules implement the standard interface:

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

**Behavior Pattern:**
```
Check if component exists in database
├─ Yes: Log "verified", return True
└─ No: Create component, verify, return True/False
```

---

## Category 1: Role Management (91 lines)

### checkroles.py (43 lines)

Verify and create PostgreSQL roles (web, sysop, term).

**Operation:**
```
Check for roles: web, sysop, term
├─ Role exists: log verified
└─ Role missing: CREATE ROLE [name]
```

**Roles Created:**
- `web` — Web interface access role
- `sysop` — System operator role
- `term` — Terminal access role

**SQL Operations:**
```sql
SELECT usename FROM pg_user WHERE usename = %s
CREATE ROLE rolename [WITH LOGIN | NOLOGIN]
```

**Returns:** `True` if all roles present, `False` on error

---

### checkwebserverrole.py (48 lines)

Verify www-data role exists (for web server access).

**Operation:**
```
Check for role: www-data
├─ Exists: log verified
└─ Missing: CREATE ROLE www-data
```

**Purpose:** Web server process needs PostgreSQL role to connect

**Returns:** `True` if www-data role exists

---

## Category 2: Extensions & Schema (85 lines)

### checkextensions.py (46 lines)

Verify and install required PostgreSQL extensions.

**Extensions Checked:**
1. `pgcrypto` — Encryption functions
2. `ltree` — Hierarchical tree structures
3. `citext` — Case-insensitive text type

**Operation:**
```
For each extension:
  Check extension installed
  ├─ Installed: log verified
  └─ Missing: CREATE EXTENSION [name]
```

**SQL Operations:**
```sql
SELECT * FROM pg_extension WHERE extname = %s
CREATE EXTENSION extname
```

**Error Handling:** Extension may fail if not available in PostgreSQL installation

**Returns:** `True` if all extensions installed, `False` if any missing

---

### checkschema.py (39 lines)

Verify `engine` schema exists; import schema.sql if needed.

**Operation:**
```
Check for schema: engine
├─ Exists: log verified
└─ Missing: 
    1. CREATE SCHEMA engine
    2. Import schema.sql
    3. Verify tables created
```

**SQL File:** `schema.sql` (location varies)

**Imports On First Run:**
- Tables (engine.member, engine.session, etc.)
- Views (lookups, statistics)
- Indexes (performance)

**Returns:** `True` if schema present and valid

---

## Category 3: Database & User Validation (228 lines)

### checkdatabase.py (78 lines)

Verify/create main BBS database.

**Operation:**
```
Check for database: bbsengine6
├─ Exists: log verified
└─ Missing: 
    1. CREATE DATABASE bbsengine6 [OWNER role] [ENCODING utf8]
    2. Log creation
    3. Verify connection
```

**Parameters:**
- Database name: `bbsengine6` (or from config)
- Owner: Usually `postgres` or sysop role
- Encoding: UTF-8 recommended

**Connection:** Must connect to `postgres` (system DB) to create new DB

**Returns:** `True` if database created or verified

---

### checksuperuser.py (55 lines)

Verify current PostgreSQL user has superuser permissions.

**Operation:**
```
Check current user privileges:
├─ Has SUPERUSER: log verified
├─ Has (CREATEDB + CREATEROLE + CANLOGIN): acceptable
└─ Else: error, insufficient privileges
```

**Checks:**
```sql
SELECT usesuper, usecreatedb, usecreaterole, usecreatedb
FROM pg_user WHERE usename = CURRENT_USER
```

**Failure Mode:** Cannot proceed if user lacks necessary permissions

**Returns:** `True` if sufficient privileges, `False` otherwise

---

### checkloginid.py (95 lines)

Verify system login ID via DBus (Linux-specific).

**Operation:**
```
Query DBus AccountsService:
├─ User found: log verified
└─ User missing: error, configure system user
```

**Linux-Specific:** Uses `dbus` to query user account properties

**Fields Accessed:**
- User UID
- Home directory
- Shell
- User name

**Failure Mode:** Non-critical on non-Linux; logs warning

**Returns:** `True` if user verified, `False` if missing

---

## Category 4: Functions & Procedures (61 lines)

### checkfunctions.py (61 lines)

Verify and import stored procedures and functions.

**Two-Stage Process:**

**Stage 0 (before database creation):**
- Core functions for role management
- Database/schema privilege functions
- Location-independent functions

**Stage 1 (after database creation):**
- Engine-specific functions
- `getflags()` — Get member flags
- `checkflag()` — Check if member has flag
- Other application logic functions

**Operation:**
```
For each function:
  Check function exists
  ├─ Exists: log verified
  └─ Missing: Import from functions.sql
```

**SQL File:** `functions.sql`

**Returns:** `True` if all functions present, `False` on error

---

## Category 5: Data Structures (214 lines)

### checkclasses.py (57 lines)

Verify class definitions (tables).

**Operation:**
```
Check for required tables:
  member, session, flag, map_member_flag, etc.
├─ Table exists: log verified
└─ Table missing: Import from schema.sql or create
```

**Tables Verified:**
- `engine.member` — Member accounts
- `engine.session` — Active sessions
- `engine.flag` — System flags
- `engine.map_member_flag` — Member-to-flag relationships
- Others as needed

**Returns:** `True` if all tables exist

---

### checkflag.py (74 lines)

Verify flag table and junction table structure.

**Operation:**
```
Check tables:
  engine.flag, engine.map_member_flag
├─ Tables exist: log verified
└─ Missing: Create and initialize
```

**Initialization:**
- Create `engine.flag` table (if missing)
- Create `engine.map_member_flag` junction table (if missing)
- Seed standard flags if needed

**Standard Flags:**
```
APPROVED, EMAILVERIFIED, SYSOP, CHATMUTE, NEWMEMBER, ...
```

**Returns:** `True` if structure verified

---

### checknotify.py (83 lines)

Verify notification system schema.

**Operation:**
```
Check notification tables:
  notification, notification_type, subscription
├─ Tables exist: log verified
└─ Missing: Create tables and types
```

**PostgreSQL Types Created:**
- `notification_type` — Enum or composite type

**Tables Verified:**
- `engine.notification` — Notification records
- `engine.subscription` — Who gets what notifications

**Returns:** `True` if notification system ready

---

## Utility Module

### createdatabase.py (29 lines)

Utility function to create database (called by checkdatabase).

**Functions:**
```python
def create_database(dbname, owner=None, encoding='UTF8'):
    # CREATE DATABASE dbname OWNER owner ENCODING encoding
```

---

## Execution Flow in Stages

### Stage 0 Sequence

```
1. Connect to 'postgres' database
2. checkroles()              ← Create web, sysop, term roles
3. checkfunctions(stage=0)   ← Load core functions
4. checksuperuser()          ← Verify user permissions
5. checkwebserverrole()      ← Verify www-data role
6. createdatabase()          ← Create BBS database
```

**Connection:** Single connection to system `postgres` database

### Stage 1 Sequence

```
1. Connect to BBS database (created in stage 0)
2. checkextensions()        ← Install pgcrypto, ltree, citext
3. checkschema()            ← Create engine schema
4. checkfunctions(stage=1)  ← Load application functions
5. checkclasses()           ← Create tables
6. checkflag()              ← Create flag tables
7. checknotify()            ← Create notification system
```

**Connection:** Separate connection to main BBS database

---

## Error Handling Pattern

**Typical Check Module:**
```python
def main(args, **kwargs) -> bool:
    try:
        # Check component exists
        if database.component_exists(...):
            io.echo("Component verified")
            return True
        
        # Create component
        database.create_component(...)
        
        # Verify creation
        if database.component_exists(...):
            io.echo("Component created successfully")
            return True
        else:
            io.echo("Failed to create component", level="error")
            return False
            
    except Exception as e:
        io.echo_traceback()
        return False
```

**Return Values:**
- `True` — Component verified or created successfully
- `False` — Component missing and could not create

**Stop-on-Failure:** Stage stops on first False return

---

## Database Connection Pattern

All checks use connection passed via kwargs:

```python
def main(args, **kwargs) -> bool:
    pool = kwargs.get('pool')
    
    with database.connect(args, pool=pool) as conn:
        with database.cursor(conn) as cur:
            # Check/create logic
        conn.commit()
    
    return True
```

---

## Common SQL Operations

### Check Existence

```sql
-- Role
SELECT usename FROM pg_user WHERE usename = %s

-- Table
SELECT * FROM information_schema.tables 
WHERE table_schema = 'engine' AND table_name = %s

-- Extension
SELECT * FROM pg_extension WHERE extname = %s

-- Function
SELECT * FROM information_schema.routines 
WHERE routine_schema = 'engine' AND routine_name = %s
```

### Create Operations

```sql
-- Role
CREATE ROLE rolename WITH [PASSWORD 'hash' | NOLOGIN]

-- Database
CREATE DATABASE dbname OWNER owner ENCODING 'UTF8'

-- Extension
CREATE EXTENSION extname

-- Schema
CREATE SCHEMA engine

-- Table
CREATE TABLE engine.member (...)
```

---

## Dependencies

**Internal:**
- `bbsengine6.database` — Connection, cursor, schema operations
- `bbsengine6.io` — Logging and error display
- `bbsengine6.console.lib` — Module framework

**External:**
- `psycopg` — PostgreSQL operations
- `dbus` — For checkloginid.py
- SQL files — `schema.sql`, `functions.sql`

