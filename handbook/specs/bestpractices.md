# bbsengine6 Best Practices

> Status: canonical. Updated 2026-09-04.

This document collects two rules that bit us in production enough to be
worth making explicit:

- [io.echo and the @variable syntax](#ioecho-and-the-variable-syntax)
- [JSON handling at the database boundary](#json-handling-at-the-database-boundary)

## io.echo and the @variable syntax

`io.echo()` interprets `{token}` escape sequences: `{restorecursor}`,
`{savecursor}`, `{promptcolor}`, `{valuecolor}`, etc. For those
sequences to be processed, the call **must** use an f-string. A plain
string is passed through verbatim and the escape sequences never get
expanded.

### Correct

```python
io.echo(f"{{restorecursor}}{{promptcolor}}{prompt}{{valuecolor}}{result}")
io.echo(f"{{labelcolor}}Item: {{valuecolor}}{item.content}{{/all}}\n")
```

### Wrong

```python
io.echo("{restorecursor}{promptcolor}...")        # escape sequences not processed
io.echo(f"{{labelcolor}}Item: {{valuecolor}}{{item.content}}{{/all}}\n")  # braces inside braces
```

The double-brace / single-brace distinction is the load-bearing part:

| Braces | Meaning |
| --- | --- |
| `{{token}}` | `io.echo` escape sequence (e.g. `{labelcolor}`) |
| `{varname}` | Python f-string substitution |

The linter rule F541 (`f-string without any placeholders`) is disabled
in the project configuration because `io.echo` calls like
`io.echo(f"{{savecursor}}")` have no Python placeholders but still
must be f-strings for the `io.echo` layer to see the escape sequences.

## JSON handling at the database boundary

Database conversions are handled by `bbsengine6.database`. **Never call
`json.dumps()` before passing data to a database function.**

> Note: `convert_for_jsonb()` wraps only the top-level dict/list in
> `Jsonb`. Inner dicts/lists are returned as plain Python objects to
> avoid the `Object of type Jsonb is not JSON serializable` error that
> psycopg's dumper raises on nested `Jsonb` instances. See
> [`database.md`](./database.md#json-bridge) for the function reference.

### The rule

```python
# WRONG - double conversion, creates non-serializable Jsonb object
rec["flags"] = json.dumps(database.convert_for_jsonb(member["flags"]))
database.update(args, table, pk, rec)

# CORRECT - let the database module handle conversion
rec["flags"] = member["flags"]   # keep as dict
database.update(args, table, pk, rec)
# database.update() calls convert_for_jsonb(rec["flags"]) internally
```

### Why this matters

The correct flow:

```
member dict
  -> buildrec(member)        # keeps dicts as dicts
  -> rec (dict with dicts)
  -> database.update()
       -> convert_for_jsonb(rec["flags"])
       -> wraps dict in psycopg3.Jsonb
  -> cur.execute(sql, [Jsonb(...)])
       -> psycopg3 serializes Jsonb -> JSONB bytes
       -> PostgreSQL stores JSONB
```

What goes wrong if you call `json.dumps` upstream:

```
buildrec() called json.dumps(convert_for_jsonb(dict))
  -> Jsonb({...}) object created
  -> json.dumps() tries to serialize it
  -> ERROR: Object of type Jsonb is not JSON serializable
```

### Layer responsibilities

Application layer (`member.py`, `console/member.py`, etc.) is allowed
to transform data structures (filter, rename, format fields), convert
lists to strings where the schema calls for it, and pass the result to
a database function. Application code must **not**:

- Call `json.dumps()` on values going to `database.update()`.
- Call `convert_for_jsonb()` before `database.update()`.
- Hand-roll `Jsonb(Jsonb(...))` constructions.
- Pre-serialize anything -- let the database layer do it.

Database layer (`database.py`) is responsible for:

- Calling `convert_for_jsonb()` on all values in `update()`,
  `insert()`, `upsert()`, `execute()`, `executemany()`.
- Wrapping the top-level dict/list in `Jsonb` and leaving inner
  structures plain.

### Patterns

**Simple values** (strings, numbers, booleans) pass through unchanged:

```python
rec = {
    "moniker": "testuser",
    "credits": 500,
    "verified": True,
}
database.update(args, table, pk, rec)
```

**Dict values** stay as dicts; the database layer wraps them:

```python
rec = {
    "flags": {
        "APPROVED": {"value": True},
        "VERIFIED": {"value": False},
    }
}
database.update(args, table, pk, rec)
```

**List values** stay as lists. The exception is the `ui` column on
`engine.__member`, which is stored as a comma-separated string and is
converted by `buildrec()`:

```python
# input
rec = {"ui": ["telnet", "web", "ssh"]}
# after buildrec()
rec = {"ui": "telnet, web, ssh"}
database.update(args, table, pk, rec)
```

**Nested dicts** stay nested:

```python
rec = {
    "settings": {
        "theme": {"dark_mode": True, "color_scheme": "solarized"},
        "notifications": {"email": True, "push": False},
    }
}
database.update(args, table, pk, rec)
# Internally: convert_for_jsonb wraps the top-level dict in Jsonb only;
# inner dicts are plain, so psycopg's dumper can serialize the whole tree.
```

### Function reference

#### `buildrec(member)` -- `bbsengine6.member`

Transforms a member dict for database operations:

- Excludes internal fields (`datecreatedepoch`, etc.).
- Keeps dict values as dicts (never as JSON strings).
- Converts the `ui` list to a comma-separated string.
- Leaves other values unchanged.

```python
input = {
    "moniker": "test",
    "flags": {"APPROVED": {"value": True}},
    "ui": ["telnet", "web"],
    "datecreatedepoch": 1234567,  # removed
}
output = buildrec(input)
# {
#     "moniker": "test",
#     "flags": {"APPROVED": {"value": True}},   # dict, not string
#     "ui": "telnet, web",
# }
```

#### `database.convert_for_jsonb(value, *, wrap=True)`

Wraps Python objects for psycopg3. Top-level dicts/lists are wrapped
in `Jsonb`; inner dicts/lists stay plain. `wrap=False` is the
recursion path used internally; callers should use the default.

```python
dict_value = {"outer": {"inner": 1}}
jsonb_value = database.convert_for_jsonb(dict_value)
type(jsonb_value)                 # psycopg.types.json.Jsonb
type(jsonb_value.obj["outer"])    # dict (plain, not Jsonb)
jsonb_value.obj                  # {'outer': {'inner': 1}}
```

#### `database.update(args, table, pk, items, ...)`

Updates rows; iterates over `items`, calls `convert_for_jsonb()` on
each value, and executes the resulting SQL. Pass plain Python dicts.

```python
database.update(args, "engine.__member", "test", {"flags": {"APPROVED": True}})
# convert_for_jsonb({"APPROVED": True}) -> Jsonb({"APPROVED": True})
# psycopg3 serializes the Jsonb to JSONB bytes
```

### Debugging checklist

If you see `TypeError: Object of type Jsonb is not JSON serializable`:

1. Remove `json.dumps()` calls from application code before passing to
   a database function.
2. Remove pre-emptive `convert_for_jsonb()` calls in application code;
   `database.update()` / `database.insert()` call it internally.
3. Replace any hand-rolled `Jsonb(Jsonb(...))` with a single
   `Jsonb({...})` over the outer dict, and let `convert_for_jsonb`
   handle the wrap.
4. Confirm `buildrec()` returns dicts as dicts (not JSON strings, not
   `Jsonb` objects).
5. Confirm `database.update()` is called with plain dicts.

### Related

- [`database.md`](./database.md#json-bridge) -- the canonical
  `convert_for_jsonb` reference.
- `py/src/bbsengine6/member/lib.py` -- `buildrec` definition.
- `py/tests/test_buildrec.py`,
  `py/tests/test_member_update_with_flags.py` -- regression coverage.
