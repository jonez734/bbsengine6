# Member Approval Workflow

## Overview

`memberapproval.py` implements the member application approval workflow. New members are created in an unapproved state and must be approved by a sysop before they can access the system.

**File:** `bbsengine6/console/memberapproval.py`  
**Size:** 128 lines  

---

## Standard Module Interface

```python
def init(args, **kwargs) -> bool
def access(args, op, **kwargs) -> bool
def buildargs(args, **kwargs) -> ArgumentParser | None
def main(args, **kwargs) -> bool
```

---

## Access Control

### access()

```python
def access(args, op, **kwargs) -> bool
```

**Requires:** `SYSOP` flag on current user

**Behavior:**
1. Gets current member from `args.session.member` (if available)
2. Checks if member has `SYSOP` flag via `member.checkflag(member, "SYSOP")`
3. Returns `True` if sysop, `False` otherwise

**Effect:** Only sysop members can approve new members

---

## Approval Workflow

### main()

```python
def main(args, **kwargs) -> bool
```

Interactive approval workflow. Processes all pending member applications.

**Workflow:**

1. **Query Pending Members**
   ```sql
   SELECT * FROM engine.member 
   WHERE approvedbyid IS NULL
   ORDER BY memberid
   ```
   Returns all unapproved members

2. **For Each Pending Member:**

   a. **Display Member Info**
      - Moniker, email, loginid
      - Creation date
      - Current flags

   b. **Email Verification**
      ```
      Email verified? (Y/n)
      ```
      - If yes: sets `EMAILVERIFIED` flag via `member.setflag()`
      - If no: skips flag

   c. **Approval Decision**
      ```
      Approve member? (Y/n)
      ```
      - If yes: continues to approval
      - If no: asks to delete or skip
         - Delete: deletes member record and associated data
         - Skip: leaves member in pending state
         - Cancel: returns to menu without changes

   d. **Set Approval Metadata**
      ```python
      approvedbyid = current_sysop_id
      approveddate = NOW()
      APPROVED = flag set
      ```

   e. **Commit Transaction**
      ```python
      conn.commit()
      ```
      Saves all flag changes and approval metadata

3. **Status Display**
   ```
   Processing Pending Members
   ==========================
   Member: alice
   Email: alice@example.com
   Created: 2024-03-15
   
   Email verified? (Y/n) _
   Approve member? (Y/n) _
   
   [Next member or completion message]
   ```

---

## Data Flow

### Pending Member Query

```python
with database.cursor(conn) as cur:
    cur.execute("""
        SELECT * FROM engine.member 
        WHERE approvedbyid IS NULL
        ORDER BY memberid
    """)
    members = cur.fetchall()
```

### Flag Operations

**Setting Flags:**
```python
member.setflag(moniker, "EMAILVERIFIED", value=True)
member.setflag(moniker, "APPROVED", value=True)
```

**Checking Current Flags:**
```python
member.checkflag(moniker, "SYSOP")  # Boolean
```

### Approval Update

```python
database.update(
    table="engine.member",
    pk="memberid",
    items={
        'approvedbyid': current_sysop_id,
        'approveddate': func.now()
    },
    primarykey="memberid"
)
```

---

## State Transitions

### New Member Created (add)
```
status: UNAPPROVED
flags: [initial flags set by creator]
approvedbyid: NULL
```

### Email Verified (optional)
```
status: UNAPPROVED (unchanged)
flags: [+ EMAILVERIFIED]
```

### Member Approved
```
status: APPROVED
flags: [+ APPROVED]
approvedbyid: [sysop memberid]
approveddate: [timestamp]
```

### Member Rejected/Deleted
```
[Record deleted from engine.member]
All associated data removed
```

---

## User Interactions

### Input Prompts

**Email Verified:**
- Prompt: `"Email verified? (Y/n) "`
- Valid responses: Y, y, yes (default: yes)
- Action: Sets EMAILVERIFIED flag if yes

**Approve Member:**
- Prompt: `"Approve member? (Y/n) "`
- Valid responses: Y, y, yes (default: yes)
- Submenu if no:
  - [D]elete member
  - [S]kip (leave unapproved)
  - [C]ancel (return to menu)

---

## Error Handling

**Database Errors:**
- Query fails → logged, workflow stops
- Update fails → transaction rolled back, error shown
- Flag set fails → logged, continues with next member

**Permission Errors:**
- Non-sysop attempts approval → access denied at module level
- Current member unknown → treated as non-sysop

**No Pending Members:**
- Query returns empty → display "No pending approvals" and exit

---

## Database Schema

### engine.member (relevant fields)

| Column | Type | Purpose |
|--------|------|---------|
| `memberid` | serial | Primary key |
| `moniker` | varchar | Username |
| `email` | varchar | Email address |
| `loginid` | varchar | System login |
| `approvedbyid` | int | FK to approver member (NULL = pending) |
| `approveddate` | timestamp | When approved (NULL = pending) |

### engine.map_member_flag

| Column | Type | Purpose |
|--------|------|---------|
| `moniker` | varchar | FK to member |
| `flagid` | varchar | FK to flag |

### engine.flag

| Column | Type | Purpose |
|--------|------|---------|
| `flagid` | varchar | Flag name (e.g., "APPROVED") |
| `description` | varchar | Human-readable description |

---

## Dependencies

**Internal:**
- `bbsengine6.member` — Member flag operations
- `bbsengine6.database` — Database connection and queries
- `bbsengine6.io` — Input/output prompts
- `bbsengine6.util` — Utility functions

**External:**
- `psycopg` — PostgreSQL operations

---

## Limitations & Future Work

**Current:**
- Only checks `approvedbyid IS NULL` (single approval state)
- No rejection reason tracking
- No email notification after approval
- No batch operations (one at a time)

**Potential Enhancements:**
- Email notification when approved
- Rejection reasons/notes storage
- Batch approve/reject
- Approval notes in database
- Audit trail of approval changes

