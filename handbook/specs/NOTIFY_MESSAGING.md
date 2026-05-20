# Notify Messaging System Specification

## Overview

The Notify Messaging System provides secure, validated messaging between users with support for individual recipients and hierarchical group targeting. This specification documents the recipient validation, group resolution, and messaging infrastructure.

**Status:** Production Ready (v1.0)  
**Files:**
- `bbsengine6/member.py` - Validation and group functions
- `bbsengine6/examples/notify_message_demo.py` - Interactive demo

---

## Moniker Validation

### Purpose

Moniker validation ensures that recipient names are valid, safe, and unambiguous for use in the messaging system. Validation occurs at the point of use (send time) to prevent FK constraint violations and security issues.

### Moniker Format Rules

All monikers must:
1. **Non-empty** - Must contain at least one character
2. **String type** - Must be a Python string
3. **No @ prefix** - Cannot start with "@" (reserved for syntax)
4. **No spaces** - Cannot contain space characters (ASCII 0x20)
5. **Max 50 characters** - Cannot exceed length limit
6. **Printable ASCII only** - Characters must be 0x20-0x7E
   - Allows: letters, numbers, punctuation (except @)
   - Blocks: UTF-8, control characters, non-ASCII

### Valid Monikers
```
alice           ✓ Simple ASCII name
bob123          ✓ With numbers
alice_bob       ✓ Underscore allowed
alice-bob       ✓ Hyphen allowed
alice.bob       ✓ Period allowed
alice@domain    ✓ @ in middle OK (not at start)
user!admin      ✓ Punctuation (except @) allowed
a               ✓ Single character OK
```

### Invalid Monikers
```
@alice          ✗ Cannot start with @
alice bob       ✗ Contains space
alice\tbob      ✗ Contains tab character
alice\nbob      ✗ Contains newline
café            ✗ Contains UTF-8 (é)
alice🎉bob      ✗ Contains emoji
alice@@bob      ✗ Double @ (first char is @)
 alice          ✗ Leading space
alice           ✗ Trailing space
aaa...aaa(51x)  ✗ Exceeds 50 character limit
```

### API: `moniker_exists()`

```python
def moniker_exists(args, moniker: str, **kwargs) -> bool | None
```

**Purpose:** Validate moniker format and check existence in database.

**Arguments:**
- `args` - Application args
- `moniker` - Moniker string to validate
- `**kwargs` - Optional: `pool`, `conn`

**Returns:**
- `True` - Moniker exists in engine.__member
- `False` - Moniker does not exist
- `None` - Error occurred (check logs)

**Raises:**
- `ValueError` - Invalid moniker format (with descriptive message)

**Examples:**
```python
from bbsengine6 import member

# Valid moniker, exists in database
result = member.moniker_exists(args, "alice", pool=pool)
# Returns: True

# Valid moniker, doesn't exist
result = member.moniker_exists(args, "nonexistent", pool=pool)
# Returns: False

# Invalid: starts with @
result = member.moniker_exists(args, "@alice", pool=pool)
# Raises: ValueError("Invalid moniker: cannot start with '@'")

# Invalid: contains space
result = member.moniker_exists(args, "alice bob", pool=pool)
# Raises: ValueError("Invalid moniker: cannot contain spaces")

# Invalid: UTF-8 character
result = member.moniker_exists(args, "café", pool=pool)
# Raises: ValueError("Invalid moniker: contains non-printable character...")
```

---

## Group Management

### Purpose

Groups allow sending messages to multiple users with a single command. Groups can contain users, other groups (nested), or both. The system automatically expands group membership recursively and prevents circular references.

### Group Format Rules

All group names must:
1. **Non-empty** - Must contain at least one character
2. **String type** - Must be a Python string
3. **Max 100 characters** - Can be longer than monikers
4. **Printable ASCII only** - Same as monikers (0x20-0x7E)
5. **No @ prefix** - Cannot start with "@"
6. **No spaces** - Cannot contain spaces (same as monikers)

**Note:** Groups are validated using the same rules as monikers, but with a higher character limit (100 vs 50).

### Valid Group Names
```
ops             ✓ Operations team
devs            ✓ Development team
all             ✓ Everyone
admins          ✓ Administrators
ops_team        ✓ With underscore
ops-team        ✓ With hyphen
team-2024       ✓ With numbers
```

### Invalid Group Names
```
@ops            ✗ Cannot start with @
ops team        ✗ Contains space
ops\t           ✗ Contains tab
café            ✗ UTF-8 not allowed
```

### Group Hierarchy

Groups can contain:
1. **User Monikers** - Individual members (alice, bob)
2. **Nested Groups** - References to other groups (ops, devs)
3. **Mixed** - Both users and groups in same group

**Example Hierarchy:**
```
all/
  ├── ops/
  │   ├── alice
  │   ├── bob
  │   └── charlie
  ├── devs/
  │   ├── dave
  │   ├── eve
  │   └── frank
  └── managers/
      ├── grace
      └── henry
```

### Circular Reference Detection

The system automatically detects and prevents circular group references with clear error messages.

**Examples of prevented circular references:**
```
ops contains ops           ✗ Circular (self-reference)
ops contains devs
devs contains ops          ✗ Circular (mutual reference)

ops contains devs
devs contains managers
managers contains ops      ✗ Circular (chain reference)
```

**Error on circular reference:**
```
ValueError: Circular group reference detected: ops is already being expanded
```

### API: `group_exists()`

```python
def group_exists(args, group_name: str, **kwargs) -> bool | None
```

**Purpose:** Validate group name format and check existence in database.

**Arguments:**
- `args` - Application args
- `group_name` - Group name to validate
- `**kwargs` - Optional: `pool`, `conn`

**Returns:**
- `True` - Group exists in engine.__notify_group
- `False` - Group does not exist
- `None` - Error occurred

**Raises:**
- `ValueError` - Invalid group name format

**Examples:**
```python
from bbsengine6 import member

# Valid group, exists
result = member.group_exists(args, "ops", pool=pool)
# Returns: True

# Valid group, doesn't exist
result = member.group_exists(args, "nonexistent", pool=pool)
# Returns: False

# Invalid: starts with @
result = member.group_exists(args, "@ops", pool=pool)
# Raises: ValueError("Invalid group name: cannot start with '@'")
```

### API: `get_group_members()`

```python
def get_group_members(args, group_name: str, **kwargs) -> list[str] | None
```

**Purpose:** Get all member monikers in a group, recursively expanding nested groups.

**Arguments:**
- `args` - Application args
- `group_name` - Group name to expand
- `**kwargs` - Optional: `pool`, `conn`

**Returns:**
- `list[str]` - List of unique member monikers (sorted)
- `[]` - Empty list if group exists but has no members
- `None` - Error occurred

**Raises:**
- `ValueError` - Invalid group name or circular reference detected

**Behavior:**
1. Validates group name format
2. Queries `engine.__notify_group` for members
3. For each member:
   - If member is a group → recursively expand with cycle detection
   - If member is a user → add to list
4. Removes duplicates (group A and B both contain alice → alice appears once)
5. Returns sorted, unique list

**Examples:**
```python
# Simple group
result = member.get_group_members(args, "ops", pool=pool)
# Returns: ["alice", "bob", "charlie"]

# Nested groups auto-expand
result = member.get_group_members(args, "all", pool=pool)
# Expands "all" which contains "ops", "devs", "managers"
# Returns: ["alice", "bob", ..., "henry"] (all unique members)

# Empty group
result = member.get_group_members(args, "empty_group", pool=pool)
# Returns: []

# Circular reference detected
try:
    result = member.get_group_members(args, "circular_group", pool=pool)
except ValueError as e:
    print(e)  # "Circular group reference detected: X is already being expanded"
```

---

## Recipient Resolution

### Purpose

Recipient resolution translates user input into a list of target monikers, handling both individual users and group expansion transparently.

### API: `MessageHandler.resolve_recipient()`

```python
def resolve_recipient(self, recipient: str) -> list[str]
```

**Purpose:** Resolve recipient (user or group name) to list of monikers.

**Arguments:**
- `recipient` - User moniker or group name string

**Returns:**
- `list[str]` - List of member monikers to send to

**Behavior:**
1. **Demo Mode** (no args/pool):
   - Returns recipient as-is in a list
   - No database validation
   - Enables testing without database

2. **Database Mode** (has args and pool):
   - Check if recipient is a group name
   - If group exists → expand to all members
   - If not group → validate as moniker
   - Return list of recipients

**Raises:**
- `ValueError` - Recipient not found or invalid

**Examples:**
```python
from notify_message_demo import DemoConfig, MessageHandler

config = DemoConfig(moniker="alice")
handler = MessageHandler(config, args=args, pool=pool)

# Individual user
result = handler.resolve_recipient("bob")
# Returns: ["bob"]

# Group (expands automatically)
result = handler.resolve_recipient("ops")
# Returns: ["alice", "bob", "charlie"] (all ops members)

# Group with nested groups
result = handler.resolve_recipient("all")
# Returns: [all unique members from all groups]

# Nonexistent recipient
try:
    result = handler.resolve_recipient("baduser")
except ValueError as e:
    print(e)  # "member baduser not found"
```

---

## Messaging Syntax

### Usage

Users send messages using @ prefix notation:

```
@<recipient> <message>
```

### Examples

**Individual messaging:**
```
@alice Hello Alice!
→ Sent to: alice only
```

**Group messaging:**
```
@ops Maintenance window 10pm-2am
→ Sent to: all ops members (alice, bob, charlie)

@all Company announcement
→ Sent to: everyone (expands all groups)
```

**With special characters:**
```
@alice_bob Message for alice_bob
@alice.bob Message for alice.bob
@alice-bob Message for alice-bob
```

### Blocked Attempts

```
@alice bob message
→ ERROR: "alice bob" not found (space not allowed in moniker)

@@ops message
→ ERROR: @ prefix cannot start with "@"

@café message
→ ERROR: UTF-8 characters not allowed

alice bob message
→ ERROR: Missing @ (ambiguous parsing)
```

---

## Demo Implementation

The `notify_message_demo.py` implements interactive messaging with full validation:

```python
from notify_message_demo import NotifyMessageDemo, DemoConfig

config = DemoConfig(moniker="alice", template="{sender}: {message}")
demo = NotifyMessageDemo(config, args=args, pool=pool)

# Interactive loop
demo.run_interactive()
```

**Available commands:**
- `@<user> <message>` - Send to individual user
- `@<group> <message>` - Send to group (expands all members)
- `?` - Show help
- `q` or `quit` - Exit
- `stats` - Show message statistics
- `F2` - View unread messages (if implemented)

---

## Error Handling

### Validation Errors

All validation errors raise `ValueError` with descriptive messages:

```python
try:
    member.moniker_exists(args, "@alice", pool=pool)
except ValueError as e:
    print(e)  # "Invalid moniker: cannot start with '@'"
    # Handle gracefully - show user-friendly error message
```

### Database Errors

Database errors (connection failure, query error) are logged via `echo_traceback()` and functions return `None`:

```python
result = member.moniker_exists(args, "alice", pool=None)
if result is None:
    # Database error occurred - check logs
    print("Error checking moniker, please try again")
```

### Circular Reference Errors

Circular groups raise clear `ValueError` with explicit detection:

```python
try:
    members = member.get_group_members(args, "circular_group", pool=pool)
except ValueError as e:
    print(e)  # "Circular group reference detected: X is already being expanded"
    # Show user that group structure has a loop
```

---

## Security Considerations

### Moniker Validation

1. **@ Prefix Check** - Prevents "@alice" monikers that could exploit syntax
2. **Space Check** - Prevents "alice bob" that could bypass parsing
3. **ASCII Only** - Blocks UTF-8 encoding attacks
4. **Length Limit** - Prevents DoS via extremely long names
5. **Format Validation** - Ensures clean, parseable recipient names

### Group Cycles

1. **Cycle Detection** - Prevents infinite loops during expansion
2. **Visited Tracking** - Uses internal `_visited` set (not exposed)
3. **Clear Errors** - Shows which group caused the cycle
4. **Early Exit** - Detects cycles immediately, not after full expansion

### Database Constraints

1. **FK Validation** - Checks recipient exists before database insert
2. **Transaction Safety** - Validation happens before writes
3. **Error Messages** - Clear "member X not found" vs database errors

---

## Performance Notes

1. **Caching** - Thread-local caching for current member
2. **Efficient Queries** - Single database lookup per unique group
3. **Duplicate Removal** - O(n) deduplication with set tracking
4. **Recursion Limit** - Practical limit via cycle detection
5. **Group Expansion** - Linear in total members + groups

**Expected Performance:**
- Single moniker lookup: ~1-2ms
- Group with 100 members: ~2-5ms
- Nested groups (3 levels, 500 total members): ~5-10ms

---

## Testing

### Test Coverage

Total: **132 tests** across all functionality

1. **Moniker validation** (27 tests)
   - Format validation (empty, length, ASCII, control chars)
   - @ prefix rejection (4 tests)
   - Space rejection (4 tests)
   - Database lookups

2. **Group validation** (25 tests)
   - Format validation
   - Existence checks
   - Member retrieval

3. **Nested groups** (11 tests)
   - Recursive expansion
   - Duplicate removal
   - Circular reference detection

4. **Integration** (61+ existing tests)
   - Demo messaging
   - Help text
   - End-to-end flows

### Running Tests

```bash
# All notification tests
pytest bbsengine6/py/tests/test_notify_message_demo.py -v

# Recipient validation tests
pytest bbsengine6/py/tests/test_notify_message_demo_recipient_validation.py -v

# Group tests
pytest bbsengine6/py/tests/test_group_recipient_resolution.py -v

# Run all together
pytest bbsengine6/py/tests/test_*.py -v
```

---

## Backward Compatibility

This feature is fully backward compatible:

1. **No breaking changes** to existing member.py API
2. **New functions only** - `moniker_exists()`, `group_exists()`, `get_group_members()`
3. **Optional integration** - Demo can be used standalone or integrated
4. **Graceful degradation** - Works in demo mode without database

---

## Future Enhancements

Possible future improvements:

1. **Group Permissions** - Admin-only group editing
2. **Group Descriptions** - Metadata for groups
3. **Temporary Groups** - Time-limited group memberships
4. **Group Broadcast** - Message delivery tracking
5. **Archived Groups** - Soft-delete with recovery
6. **Group Analytics** - Member activity reports
7. **Regex Groups** - Pattern-based dynamic groups

---

## References

**Related Specs:**
- `member.md` - Core member functions
- `console/notify.md` - Notification system (stub)

**Database Tables:**
- `engine.__member` - User monikers
- `engine.__notify_group` - Group memberships
- `engine.__notify` - Messages
- `engine.__notify_recipient` - Message recipients

**Source Files:**
- `py/src/bbsengine6/member.py` - Implementation
- `py/src/bbsengine6/examples/notify_message_demo.py` - Demo
- `py/tests/test_*.py` - Comprehensive tests
