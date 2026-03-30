# Member Management Module

## Overview

`member.py` provides complete member CRUD operations through an interactive menu-driven interface. Handles member creation, editing, flag management, and database role configuration.

**File:** `bbsengine6/console/member.py`  
**Size:** 610 lines  

---

## Standard Module Interface

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

All functions follow standard console module interface requirements.

---

## Public API

### add()

```python
def add(args, **kwargs) -> bool
```

Interactive member creation. Prompts for all required fields.

**Fields Collected:**
- `moniker` — Username (must be unique)
- `loginid` — System login ID
- `email` — Email address
- `password` — Member password (hashed via `libmember.setpassword()`)
- `credits` — Initial credits
- `ui` — Interface preference (web/terminal)
- `sysop` — Is sysop flag (yes/no)

**Validation:**
- Moniker must be unique (checks existing members)
- All required fields must be provided
- Email format validated

**Database Operations:**
1. `libmember.insert(moniker, loginid, email)` — Create member row
2. `libmember.setpassword(moniker, password)` — Hash and store password
3. `libmember.setcredits(moniker, credits)` — Set credit balance
4. `configurerole(args, moniker, sysop)` — Create database role with permissions
5. `conn.commit()` — Commit transaction

**Returns:** `True` on success, `False` on validation error or database failure

---

### edit()

```python
def edit(args, **kwargs) -> bool
```

Interactive member selection and editing menu.

**Behavior:**
1. Prompts user for member moniker to edit
2. Loads member from database via `libmember.find(moniker)`
3. Calls `_edit(args, "edit", member)` for interactive editing
4. On completion, commits changes to database

**Returns:** `True` on success, `False` if member not found

---

### _edit()

```python
def _edit(args, mode, member, **kwargs) -> bool
```

Interactive member editing interface. Used for both add (mode="add") and edit (mode="edit").

**Behavior:**
1. Deep copies original member for comparison: `original = copy.deepcopy(member)`
2. For each editable field:
   - Displays current value (highlighted if changed from original)
   - Prompts for new value
   - Updates member object if user provides input
3. After all fields, displays summary of changes
4. Asks for confirmation before saving

**Fields:**
- `moniker` — Member name (immutable in edit mode)
- `loginid` — System login
- `email` — Email address
- `password` — Password (shown as masked on entry)
- `credits` — Account credits
- `ui` — Interface (web/terminal)
- `flags` — System flags via `editflags()`
- `sysop` — Sysop access (calls `editui()` to configure role)

**Display Style:**
```
Member Details
==============
Moniker: alice
LoginID: alice_user
Email: alice@example.com
[Changes highlighted in color]

Confirm save? (Y/n)
```

**Returns:** `True` if changes saved, `False` if cancelled

---

### editflags()

```python
def editflags(args, moniker, **kwargs) -> bool
```

Interactive member flag editor. Displays all system flags with current state.

**Behavior:**
1. Loads all flags from `engine.flag` table
2. For each flag:
   - Displays flag name and description
   - Shows current state (set/unset)
   - Prompts to toggle
3. Updates `engine.map_member_flag` junction table

**Common Flags:**
- `APPROVED` — Member account approved
- `EMAILVERIFIED` — Email verified
- `SYSOP` — System operator
- `CHATMUTE` — Chat muted
- `NEWMEMBER` — New member marker

**Returns:** `True` on completion, `False` on database error

---

### editui()

```python
def editui(args, rolename) -> bool
```

Configures UI preference (web vs terminal) for member's database role.

**Behavior:**
1. Calls `setui(args, rolname, "web" or "term")`
2. Grants/revokes privileges for web interface access

**Parameters:**
- `rolename` — Member's database role name
- `ui` — "web" or "term" (determined by member preference)

**Returns:** `True` on success

---

### configurerole()

```python
def configurerole(args, rolename, sysop, **kwargs) -> bool
```

Creates member database role with appropriate permissions.

**Behavior:**
1. Checks if role exists: `database.roleexists()`
2. If not exists:
   - Creates role via `database.createrole(rolename)`
   - Sets password hash
3. Calls `setui()` to configure interface permissions
4. If sysop=True: grants sysop permissions

**Parameters:**
- `rolename` — Role name (typically member moniker)
- `sysop` — Whether to grant sysop permissions

**Permissions:**
- Basic: CONNECT, USAGE on schema
- Web UI: Additional tables for web access
- Sysop: Administrative privileges

**Returns:** `True` on success, `False` on database error

---

### setui()

```python
def setui(args, rolname, ui, **kwargs) -> bool
```

Grants or revokes web interface permissions on a member role.

**Behavior:**
1. If `ui="web"`:
   - Grants SELECT/INSERT/UPDATE/DELETE on web tables
2. If `ui="term"`:
   - Revokes all web table permissions

**Implementation:**
- Uses `database.grantrole()` and `database.revokerole()`
- Operates on `engine` schema and public tables

**Returns:** `True` on success

---

### main()

```python
def main(args, **kwargs) -> bool
```

Interactive member management menu. Main entry point.

**Behavior:**
1. Displays member management menu
2. Loops until user exits

**Menu Options:**

| Option | Action |
|--------|--------|
| [E]dit | Call `edit()` |
| [N]ew | Call `add()` |
| [A]pprovals | Call `memberapproval.main()` |
| [Q]uit | Return `True` |

**Status Display:**
- Total member count
- System status

**Returns:** `True` on exit

---

## Helper Functions

### help()

```python
def help(args, **kwargs) -> bool
```

Display detailed member information. Used in edit workflow.

**Displays:**
- Current member data
- Changed fields highlighted
- Comparison with original values

---

### showui()

```python
def showui(args, ui, _ui) -> str
```

Format UI preference for display.

**Returns:** "Web" or "Terminal" based on ui parameter

---

## Data Structures

### Member Object

Member dictionary (from `libmember.find()`):
```python
{
    'moniker': 'alice',
    'loginid': 'alice_user',
    'email': 'alice@example.com',
    'password': 'hashed_password',
    'credits': 1000,
    'ui': 'web',  # or 'term'
    'sysop': True,  # or False
    'created': datetime,
    'lastlogin': datetime,
    # ... other fields
}
```

### Flag Object

Flag record (from `engine.flag` table):
```python
{
    'flagid': 'APPROVED',
    'description': 'Member account approved',
    'value': 1  # or 0
}
```

---

## Database Operations

**Queries:**
- `SELECT * FROM engine.member WHERE moniker = %s` — Find member
- `SELECT * FROM engine.flag` — Get all flags
- `SELECT flag FROM engine.map_member_flag WHERE moniker = %s` — Get member flags

**Mutations:**
- `INSERT INTO engine.member (moniker, loginid, email) VALUES ...` — Create member
- `UPDATE engine.member SET ... WHERE moniker = %s` — Update member
- `INSERT INTO engine.map_member_flag (moniker, flagid) VALUES ...` — Set flag
- `DELETE FROM engine.map_member_flag WHERE moniker = %s AND flagid = %s` — Unset flag

**Role Operations:**
- `CREATE ROLE rolename ...` — Create database role
- `GRANT ... ON SCHEMA engine TO rolename` — Grant schema access
- `GRANT ... ON public.* TO rolename` — Grant table access

---

## Error Handling

**Validation Errors:**
- Moniker already exists → show error, prompt again
- Missing required field → highlight, prompt again
- Invalid email format → show error, prompt again

**Database Errors:**
- Insert fails → rollback, log error, return False
- Role creation fails → log error, continue (role may exist)
- Commit fails → rollback, return False

**User Cancellation:**
- User cancels edit → no changes saved
- User cancels confirmation → no database changes

---

## Dependencies

**Internal:**
- `bbsengine6.member` (imported as `libmember`) — Member entity operations
- `bbsengine6.database` — Database connection and operations
- `bbsengine6.io` — Input/output prompts
- `bbsengine6.util` — Utility functions
- `bbsengine6.console.memberapproval` — Approval workflow

**External:**
- `copy` — Deep copy for change tracking
- `bcrypt` — Password hashing (via libmember)

