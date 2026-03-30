# JSON/JSONB Handling Guide for bbsengine6

## Core Principle

**Database conversions are handled by `database.py`. Never call `json.dumps()` before passing data to database functions.**

---

## The Rule

### ❌ DON'T DO THIS:
```python
# WRONG - Double conversion, creates non-serializable Jsonb object
rec["flags"] = json.dumps(database.convert_for_jsonb(member["flags"]))
database.update(args, table, pk, rec)
```

### ✅ DO THIS INSTEAD:
```python
# CORRECT - Let database module handle conversion
rec["flags"] = member["flags"]  # Keep as dict
database.update(args, table, pk, rec)
# database.update() calls convert_for_jsonb() on each value internally
```

---

## Why This Matters

### The Data Flow (CORRECT)

```
Application Layer          Database Layer           PostgreSQL
─────────────────         ──────────────           ──────────
member dict
  ↓
buildrec(member)
  → keeps dicts as dicts
  ↓
rec (dict with dicts)
  ↓
database.update()
  → calls convert_for_jsonb(rec["flags"])
  → wraps dict in psycopg3.Jsonb
  ↓
cur.execute(sql, [Jsonb(...)])
                                  ↓
                            psycopg3 serializes
                            Jsonb → JSONB bytes
                                       ↓
                                  PostgreSQL
                                  stores JSONB
```

### What Went Wrong (BROKEN)

```
buildrec() called:
  json.dumps(convert_for_jsonb(dict))
    ↓
  Jsonb({...}) object created
    ↓
  json.dumps() tries to serialize it
    ↓
  ERROR: Object of type Jsonb is not JSON serializable
```

---

## Layer Responsibilities

### Application Layer (member.py, console/member.py, etc.)

✅ **DO**:
- Transform data structures (filter, rename, format fields)
- Convert lists to strings when needed
- Keep dicts and complex types as-is
- Pass data to database functions

❌ **DON'T**:
- Call `json.dumps()` on values going to `database.update()`
- Call `convert_for_jsonb()` before `database.update()`
- Assume you need to pre-serialize anything

### Database Layer (database.py)

✅ **DO**:
- Call `convert_for_jsonb()` on all values in `update()` and `insert()`
- Handle psycopg3 type conversions (Jsonb, Json, etc.)
- Serialize for database transmission

### psycopg3 Library

✅ **DO**:
- Serialize Jsonb objects to JSONB bytes
- Send to PostgreSQL
- Handle all database type conversions

---

## Common Patterns

### Pattern 1: Simple Values (strings, numbers, booleans)

```python
# These pass through unchanged
rec = {
    "moniker": "testuser",      # string → string
    "credits": 500,             # int → int
    "verified": True,           # bool → bool
}
database.update(args, table, pk, rec)
# database.update() calls convert_for_jsonb() on each
# convert_for_jsonb() returns them as-is
# psycopg3 sends them to PostgreSQL
```

### Pattern 2: Dict Values (JSONB data)

```python
# Keep as dict, let database.py wrap it
rec = {
    "flags": {
        "APPROVED": {"value": True},
        "VERIFIED": {"value": False},
    }
}
database.update(args, table, pk, rec)
# database.update() calls convert_for_jsonb(rec["flags"])
# Returns Jsonb({...})
# psycopg3 serializes to JSONB bytes
# PostgreSQL stores as JSONB column
```

### Pattern 3: List Values (JSONB arrays)

```python
# Keep as list
rec = {
    "ui": ["telnet", "web", "ssh"]
}
# But buildrec() converts it to comma-separated string!
rec = {
    "ui": "telnet, web, ssh"  # UI is special case
}
database.update(args, table, pk, rec)
# In this case it's a string, so passes through
```

### Pattern 4: Nested Dicts (Complex JSONB)

```python
# Nested structures are fine - just keep as dicts
rec = {
    "settings": {
        "theme": {
            "dark_mode": True,
            "color_scheme": "solarized"
        },
        "notifications": {
            "email": True,
            "push": False
        }
    }
}
database.update(args, table, pk, rec)
# database.update() → convert_for_jsonb() → recursively wraps
# Result: Jsonb({
#   "settings": Jsonb({
#     "theme": Jsonb({...}),
#     "notifications": Jsonb({...})
#   })
# })
```

---

## Function Reference

### buildrec(member)

**Purpose**: Transform member dict for database operations

**Input**: Dict with member fields (may include dicts, lists, etc.)

**Output**: Dict with:
- Excluded fields removed (datecreatedepoch, attrs, etc.)
- Dict values kept as dicts (NOT JSON strings)
- List values converted to comma-separated strings (UI field only)
- Other values unchanged

**Key**: Returns dicts as dicts, not JSON strings

```python
input = {
    "moniker": "test",
    "flags": {"APPROVED": {"value": True}},
    "ui": ["telnet", "web"],
    "datecreatedepoch": 1234567,  # Will be removed
}
output = buildrec(input)
# {
#     "moniker": "test",
#     "flags": {"APPROVED": {"value": True}},  # dict, not string!
#     "ui": "telnet, web",
# }
```

### database.convert_for_jsonb(value)

**Purpose**: Convert Python objects to psycopg3 types for database storage

**Input**: Any Python value

**Output**: 
- Dicts → Jsonb({...})
- Lists/tuples → Jsonb([...])
- Datetimes → ISO string
- Strings, ints, floats, bools → unchanged
- Other types → converted to string

**Key**: Returns psycopg3 types, not JSON strings

```python
dict_value = {"key": "value"}
jsonb_value = database.convert_for_jsonb(dict_value)
print(type(jsonb_value))  # <class 'psycopg.types.json.Jsonb'>
print(jsonb_value.obj)    # {'key': 'value'}
```

### database.update(args, table, pk, items, ...)

**Purpose**: Update rows in database table

**Input**: items dict with column:value pairs

**Process**:
1. Iterates over items
2. Calls `convert_for_jsonb(value)` on each value
3. Executes SQL with converted values
4. psycopg3 serializes Jsonb objects

**Key**: You pass plain Python dicts, this function handles conversion

```python
rec = {
    "moniker": "test",
    "flags": {"APPROVED": True},  # Plain dict
}
database.update(args, "engine.__member", "test", rec)
# Internally: convert_for_jsonb(rec["flags"]) wraps in Jsonb
# Internally: psycopg3 serializes to JSONB bytes
```

---

## Debugging Checklist

If you get `TypeError: Object of type Jsonb is not JSON serializable`:

1. ❌ Check for `json.dumps()` calls in application code
   - Remove them before passing to database functions
   
2. ❌ Check for double `convert_for_jsonb()` calls
   - Don't call it in application code
   - `database.update()` calls it internally
   
3. ✅ Verify buildrec() returns dicts as dicts
   - Should NOT be JSON strings
   - Should NOT be Jsonb objects
   
4. ✅ Verify database.update() is called with plain dicts
   - Not JSON strings
   - Not Jsonb objects

---

## References

- **Fix File**: `bbsengine6/py/src/bbsengine6/member.py:76` (buildrec function)
- **Database File**: `bbsengine6/py/src/bbsengine6/database.py:21` (convert_for_jsonb function)
- **Related Code**: `bbsengine6/py/src/bbsengine6/database.py:341` (where convert_for_jsonb is called)
- **Test Cases**: `bbsengine6/py/tests/test_buildrec.py` and `test_member_update_with_flags.py`

---

**Last Updated**: March 28, 2026
**Status**: Finalized after fix completion
