# Data Flows: Complete Workflows

## Overview

This section documents the complete call sequences and data transformations for key console workflows.

---

## Workflow 1: Database Initialization (Stage 0)

**Trigger:** `zoidoffice` (no args) → `main.stage_zero()`

**Sequence:**

```
1. Connect to PostgreSQL 'postgres' database
   └─ DSN: postgres://user@localhost/postgres
   └─ Connection pool created

2. lib.checkroles()
   └─ Query: SELECT usename FROM pg_user WHERE usename IN ('web','sysop','term')
   ├─ If missing: CREATE ROLE web [NOLOGIN]
   ├─ If missing: CREATE ROLE sysop [NOLOGIN]
   └─ If missing: CREATE ROLE term [NOLOGIN]
   └─ Return: True if all roles exist

3. lib.checkfunctions(stage=0)
   └─ Load core functions from functions.sql
   ├─ Verify functions exist in postgres DB
   └─ Return: True if all functions present

4. lib.checksuperuser()
   └─ Query: SELECT usesuper FROM pg_user WHERE usename = CURRENT_USER
   ├─ If SUPERUSER: Return True
   ├─ Else if (CREATEDB + CREATEROLE + CANLOGIN): Return True
   └─ Else: Return False (ERROR: insufficient permissions)

5. lib.checkwebserverrole()
   └─ Query: SELECT usename FROM pg_user WHERE usename = 'www-data'
   ├─ If found: Return True
   └─ If missing: CREATE ROLE www-data; Return True

6. lib.createdatabase()
   └─ Query: SELECT datname FROM pg_database WHERE datname = 'bbsengine6'
   ├─ If found: Return True
   └─ If missing:
       1. CREATE DATABASE bbsengine6 OWNER postgres ENCODING 'UTF8'
       2. Verify connection to new database
       3. Return True

Exit: Return True (success) or False (failure at any step)
```

---

## Workflow 2: Database Initialization (Stage 1)

**Trigger:** Stage 0 succeeds → `main.stage_one()`

**Sequence:**

```
1. Connect to BBS database (bbsengine6)
   └─ DSN: postgres://user@localhost/bbsengine6
   └─ Reuses connection pool

2. lib.checkextensions()
   └─ For each (pgcrypto, ltree, citext):
       1. Query: SELECT extname FROM pg_extension WHERE extname = %s
       2. If missing: CREATE EXTENSION extname
   └─ Return: True if all installed

3. lib.checkschema()
   └─ Query: SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'engine'
   ├─ If found: Return True
   └─ If missing:
       1. CREATE SCHEMA engine
       2. Load and execute schema.sql
       3. Verify tables created
       4. Return True

4. lib.checkfunctions(stage=1)
   └─ Load engine-specific functions from functions.sql
   └─ Verify functions exist
   └─ Return: True

5. lib.checkclasses()
   └─ Verify tables exist: member, session, flag, map_member_flag, etc.
   └─ Return: True if all present

6. lib.checkflag()
   └─ Verify: engine.flag, engine.map_member_flag tables
   └─ Seed standard flags if needed
   └─ Return: True

7. lib.checknotify()
   └─ Verify notification tables and types
   └─ Return: True

Exit: Return True (success) or False (failure at any step)
```

---

## Workflow 3: Add New Member

**Trigger:** Console menu → [M]embers → [N]ew

**Sequence:**

```
1. member.add(args, **kwargs)
   └─ Call member._edit(args, "add", {})

2. _edit() - Interactive form loop
   └─ Display form with fields:
       moniker, loginid, email, password, credits, ui, sysop
   └─ For each field:
       1. Prompt user for input
       2. Validate input
       3. Update member dict
       4. If validation fails: prompt again
   └─ Display summary of changes
   └─ Prompt: "Confirm save? (Y/n)"

3. If confirmed - Database operations:
   
   a. libmember.insert(moniker, loginid, email)
      └─ INSERT INTO engine.member (moniker, loginid, email, ...)
      └─ Returns member dict with memberid

   b. libmember.setpassword(moniker, password)
      └─ Hash password with bcrypt
      └─ UPDATE engine.member SET password = %s WHERE moniker = %s

   c. libmember.setcredits(moniker, credits)
      └─ UPDATE engine.member SET credits = %s WHERE moniker = %s

   d. For each flag (e.g., APPROVED):
      └─ libmember.setflag(moniker, flagid, value=True)
      └─ INSERT INTO engine.map_member_flag (moniker, flagid)

   e. configurerole(args, moniker, sysop)
      ├─ Check if role exists: SELECT usename FROM pg_user WHERE usename = %s
      ├─ If missing: database.createrole(moniker)
      ├─ Call setui(args, moniker, member['ui'])
      │   └─ GRANT ... or REVOKE ... on tables
      └─ If sysop=True: Grant sysop privileges

   f. conn.commit()
      └─ Transaction committed

4. Return True (success) or False (error/cancel)
```

---

## Workflow 4: Approve Pending Member

**Trigger:** Console menu → [M]embers → [A]pprovals

**Sequence:**

```
1. memberapproval.access(args, "run")
   └─ Check current member has SYSOP flag
   └─ If no: Return False (access denied)

2. memberapproval.main(args)
   
   3. Query pending members:
      └─ SELECT * FROM engine.member WHERE approvedbyid IS NULL
      
   4. For each pending member:
      
      a. Display member info:
         ├─ Moniker, Email, LoginID
         ├─ Creation date
         └─ Current flags
      
      b. Prompt: "Email verified? (Y/n)"
         └─ If yes:
            └─ libmember.setflag(moniker, "EMAILVERIFIED", True)
            └─ INSERT INTO engine.map_member_flag...
      
      c. Prompt: "Approve member? (Y/n)"
         └─ If yes:
            └─ Update member:
               UPDATE engine.member
               SET approvedbyid = %s,
                   approveddate = NOW()
               WHERE moniker = %s
            
            └─ libmember.setflag(moniker, "APPROVED", True)
            └─ INSERT INTO engine.map_member_flag...
         
         └─ If no:
            ├─ Submenu: [D]elete, [S]kip, [C]ancel
            ├─ If Delete: DELETE FROM engine.member WHERE moniker = %s
            ├─ If Skip: Leave unapproved
            └─ If Cancel: Revert and return
      
      d. conn.commit()
         └─ Changes committed
   
   5. Next member or completion

Return: True (workflow complete)
```

---

## Workflow 5: View Active Sessions

**Trigger:** Console menu → [S]essions

**Sequence:**

```
1. session.main(args, pool=pool)

2. Query active sessions:
   └─ SELECT * FROM engine.session 
      WHERE expires > NOW()
      ORDER BY created DESC

3. For each session row:
   
   a. Extract fields:
      ├─ moniker (member name)
      ├─ created (when logged in)
      ├─ expires (when expires)
      ├─ lastactivity (last activity time)
      └─ useragent (browser/client info)
   
   b. Calculate time remaining:
      └─ remaining = expires - NOW()
      └─ Format: "1h 23m 45s" or "EXPIRED"
   
   c. Calculate last activity time:
      └─ ago = NOW() - lastactivity
      └─ Format: "5m ago", "23h ago", "Just now"
   
   d. Display row in table format:
      moniker | created | expires | lastactivity

4. Display summary:
   └─ Total Sessions: N

5. Menu options:
   ├─ [R]efresh
   ├─ [X]it
   └─ Return to main menu

Return: True
```

---

## Data Structures in Flight

### Member During Add Workflow

```python
# Initial (empty add)
member = {}

# After user input
member = {
    'moniker': 'alice',
    'loginid': 'alice_user',
    'email': 'alice@example.com',
    'password': 'plaintext_password',  # plaintext in form
    'credits': 1000,
    'ui': 'web',
    'sysop': False
}

# After database operations
member = {
    'memberid': 42,  # assigned by DB
    'moniker': 'alice',
    'loginid': 'alice_user',
    'email': 'alice@example.com',
    'password': '$2b$12$...',  # hashed
    'credits': 1000,
    'ui': 'web',
    'sysop': False,
    'created': datetime.now(),
    'lastlogin': None,
    'approvedbyid': None,
    'flags': ['NEWMEMBER']  # if set during creation
}
```

### Session Row During Display

```python
# From database.cursor() as dict
session = {
    'sessionid': 'uuid-string-12345',
    'moniker': 'alice',
    'created': datetime(2024, 3, 15, 10, 30, 0),
    'expires': datetime(2024, 3, 15, 12, 30, 0),
    'lastactivity': datetime(2024, 3, 15, 11, 15, 32),
    'useragent': 'Mozilla/5.0...'
}

# Formatted for display
display = {
    'moniker': 'alice',
    'created': '2024-03-15 10:30:00',
    'expires': '2024-03-15 12:30:00',
    'remaining': '1h 14m 28s',
    'lastactivity': '45m ago',
}
```

---

## Transaction Boundaries

### Member Add Transaction

```
BEGIN
  INSERT INTO engine.member (...)
  UPDATE engine.member SET password = ... WHERE moniker = ...
  INSERT INTO engine.map_member_flag (...)
  CREATE ROLE moniker ...
  GRANT ... ON SCHEMA engine TO moniker
COMMIT (or ROLLBACK on error)
```

### Member Approval Transaction

```
For each member:
  BEGIN
    UPDATE engine.member SET approvedbyid, approveddate WHERE moniker = ...
    INSERT INTO engine.map_member_flag (EMAILVERIFIED, APPROVED)
  COMMIT (or ROLLBACK on error)
```

### Database Setup Transactions

```
Each check module: BEGIN ... COMMIT
  Stage 0: Separate transaction per check
  Stage 1: Separate transaction per check
```

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
If database error during approval:
  └─ Transaction rolled back
  └─ Error logged and displayed
  └─ User can retry same member or continue to next
```

### Failed Stage Setup

```
If stage_zero fails at step N:
  └─ Stop immediately
  └─ Log error with details
  └─ User must fix issue and restart

If stage_one fails at step N:
  └─ Database already exists
  └─ Can restart stage_one independently
```

