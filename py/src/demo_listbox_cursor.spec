# demo_listbox_cursor Specification

## Overview

`demo_listbox_cursor` demonstrates the `ListboxCursor` widget which extends `Listbox` to support lazy-loading items from a database cursor. It displays a scrollable list of US Presidents from the `article2.president` table.

## Architecture

- **ListboxCursor**: Subclass of `Listbox` that overrides `fetchitems()` to lazy-load one page at a time from a scrollable database cursor
- **Article2PresidentListboxItem**: Custom `ListboxItem` subclass that maps database rows to listbox items

## Database Requirements

- Database: Must exist (checked via `database.exists()`)
- Schema: `article2` must exist (checked via `database.schemaexists()`)
- Tables: `article2.president`, `article2.person`, `article2.trait`

## Usage

```bash
python demo_listbox_cursor.py --databasename yummyjam --databasehost localhost
```

## Command-line Arguments

| Argument | Description |
|----------|-------------|
| `--databasename` | Database name (default: yummyjam) |
| `--databasehost` | Database host (default: localhost) |
| `--databaseport` | Database port (default: 5432) |
| `--databaseuser` | Database user |
| `--databasepassword` | Database password |
| `--debug` | Enable debug output |
| `--verbose` | Enable verbose output |

## Custom Keys

| Key | Action |
|-----|--------|
| Enter | Select current item |
| E | Edit current item (displays pk) |
| KEY_INS | Insert new record (shows message) |
| Escape | Cancel selection |

## Error Handling

- Checks database existence before connecting
- Checks schema existence before querying
- Catches `psycopg.DatabaseError` exceptions
- Returns appropriate error codes on failure

## Key Functions

- `database.getpool(args, dbname=...)`: Create connection pool (as context manager)
- `database.exists(args, databasename, pool=pool)`: Check if database exists
- `database.schemaexists(args, schemaname, pool=pool)`: Check if schema exists
- `database.connect(args, pool=pool)`: Get connection from pool (as context manager)
- `database.cursor(conn)`: Create cursor (as context manager)
